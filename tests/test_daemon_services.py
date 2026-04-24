# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for seiscat daemon service artifact generation."""

import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import call, patch

from seiscat.daemon.services import (
    _LAUNCHD_LABEL,
    _SYSTEMD_SERVICE,
    _uninstall_systemd,
    show_status,
    render_launchd_plist,
    render_systemd_service,
    render_systemd_timer,
)


def _make_config(**overrides):
    return {
        'daemon_enabled': True,
        'daemon_interval': '15 minutes',
        'daemon_run_fetch_event': False,
        'daemon_run_fetch_data': False,
        'daemon_jitter_seconds': 0,
        'daemon_lock_timeout_seconds': 300,
        'daemon_log_file': None,
        'daemon_state_file': None,
    } | overrides


FAKE_CONFIGFILE = '/home/user/project/seiscat.conf'
FAKE_EXE = '/usr/local/bin/seiscat'
FAKE_WORKING_DIR = str(pathlib.Path(FAKE_CONFIGFILE).resolve().parent)


# ---------------------------------------------------------------------------
# launchd plist rendering
# ---------------------------------------------------------------------------

class TestRenderLaunchdPlist(unittest.TestCase):
    """Test that the launchd plist renders correctly."""

    def setUp(self):
        # Patch _seiscat_invocation so tests don't depend on system PATH
        import seiscat.daemon.services as ds
        self._orig = ds._seiscat_invocation
        ds._seiscat_invocation = (
            lambda cf: [FAKE_EXE, 'daemon', '-c', cf, 'run'])

    def tearDown(self):
        import seiscat.daemon.services as ds
        ds._seiscat_invocation = self._orig

    def test_label_present(self):
        plist = render_launchd_plist(_make_config(), FAKE_CONFIGFILE)
        self.assertIn(_LAUNCHD_LABEL, plist)

    def test_start_interval_matches_daemon_interval(self):
        # 15 minutes = 900 seconds
        plist = render_launchd_plist(_make_config(), FAKE_CONFIGFILE)
        self.assertIn('<integer>900</integer>', plist)

    def test_start_interval_1_hour(self):
        plist = render_launchd_plist(
            _make_config(daemon_interval='1 hour'), FAKE_CONFIGFILE
        )
        self.assertIn('<integer>3600</integer>', plist)

    def test_program_arguments_contain_exe(self):
        plist = render_launchd_plist(_make_config(), FAKE_CONFIGFILE)
        self.assertIn(FAKE_EXE, plist)
        self.assertIn(FAKE_CONFIGFILE, plist)

    def test_working_directory_set_from_configfile(self):
        plist = render_launchd_plist(_make_config(), FAKE_CONFIGFILE)
        self.assertIn('<key>WorkingDirectory</key>', plist)
        self.assertIn(f'<string>{FAKE_WORKING_DIR}</string>', plist)

    def test_custom_log_file(self):
        plist = render_launchd_plist(
            _make_config(daemon_log_file='/tmp/seiscat.log'), FAKE_CONFIGFILE
        )
        self.assertIn('/tmp/seiscat.log', plist)

    def test_valid_xml_structure(self):
        plist = render_launchd_plist(_make_config(), FAKE_CONFIGFILE)
        self.assertTrue(plist.strip().startswith('<?xml'))
        self.assertIn('<plist version="1.0">', plist)
        self.assertIn('</plist>', plist)


# ---------------------------------------------------------------------------
# systemd service unit rendering
# ---------------------------------------------------------------------------

class TestRenderSystemdService(unittest.TestCase):
    """Test that the systemd service unit renders correctly."""

    def setUp(self):
        import seiscat.daemon.services as ds
        self._orig = ds._seiscat_invocation
        ds._seiscat_invocation = (
            lambda cf: [FAKE_EXE, 'daemon', '-c', cf, 'run'])

    def tearDown(self):
        import seiscat.daemon.services as ds
        ds._seiscat_invocation = self._orig

    def test_exec_start_contains_exe(self):
        unit = render_systemd_service(_make_config(), FAKE_CONFIGFILE)
        self.assertIn(FAKE_EXE, unit)
        self.assertIn(FAKE_CONFIGFILE, unit)

    def test_working_directory_set_from_configfile(self):
        unit = render_systemd_service(_make_config(), FAKE_CONFIGFILE)
        self.assertIn(f'WorkingDirectory={FAKE_WORKING_DIR}', unit)

    def test_type_oneshot(self):
        unit = render_systemd_service(_make_config(), FAKE_CONFIGFILE)
        self.assertIn('Type=oneshot', unit)

    def test_custom_log_file(self):
        unit = render_systemd_service(
            _make_config(daemon_log_file='/tmp/seiscat.log'), FAKE_CONFIGFILE
        )
        self.assertIn('/tmp/seiscat.log', unit)

    def test_after_network(self):
        unit = render_systemd_service(_make_config(), FAKE_CONFIGFILE)
        self.assertIn('network-online.target', unit)


# ---------------------------------------------------------------------------
# systemd timer unit rendering
# ---------------------------------------------------------------------------

class TestRenderSystemdTimer(unittest.TestCase):
    """Test that the systemd timer unit renders correctly."""

    def test_on_active_sec_15_minutes(self):
        timer = render_systemd_timer(_make_config())
        self.assertIn('OnActiveSec=900s', timer)

    def test_on_unit_active_sec_15_minutes(self):
        timer = render_systemd_timer(_make_config())
        # 15 minutes = 900s
        self.assertIn('OnUnitActiveSec=900s', timer)

    def test_on_unit_active_sec_1_hour(self):
        timer = render_systemd_timer(_make_config(daemon_interval='1 hour'))
        self.assertIn('OnUnitActiveSec=3600s', timer)

    def test_service_unit_reference(self):
        timer = render_systemd_timer(_make_config())
        self.assertIn(_SYSTEMD_SERVICE, timer)

    def test_wanted_by_timers_target(self):
        timer = render_systemd_timer(_make_config())
        self.assertIn('WantedBy=timers.target', timer)

    def test_persistent_true(self):
        timer = render_systemd_timer(_make_config())
        self.assertIn('Persistent=true', timer)


class TestShowStatus(unittest.TestCase):
    """Test config-free daemon status discovery."""

    @staticmethod
    def _write_instance_files(tmp, state):
        """Write state and registry files for one daemon instance."""
        state_file = tmp / 'state.json'
        registry_file = tmp / 'daemon_instance.abcd1234.json'
        state['instance']['state_file'] = str(state_file)
        state['instance']['lock_file'] = str(tmp / 'daemon.abcd1234.lock')
        state_file.write_text(json.dumps(state), encoding='utf-8')
        registry_file.write_text(
            json.dumps(state['instance']),
            encoding='utf-8',
        )

    def test_status_discovers_instance_without_config(self):
        state = {
            'instance': {
                'tag': 'abcd1234',
                'config_file': '/tmp/demo/seiscat.conf',
                'db_file': '/tmp/demo/seiscat.sqlite',
                'state_file': '/tmp/demo/state.json',
                'lock_file': '/tmp/demo/daemon.lock',
            },
            'last_run': {
                'started_at': '2026-04-24T09:00:00+00:00',
                'status': 'success',
                'stages': {
                    'updatedb': {
                        'status': 'success',
                        'elapsed_s': 0.5,
                    }
                },
            },
        }
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            self._write_instance_files(tmp, state)
            (tmp / 'seiscat-daemon.timer').write_text('', encoding='utf-8')
            stdout = io.StringIO()
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.services._systemd_unit_dir',
                    return_value=tmp,
                ),
                patch('seiscat.daemon.services._systemctl'),
                patch('seiscat.daemon.services.sys.platform', 'linux'),
                patch('sys.stdout', new=stdout),
            ):
                show_status({'args': object()})
        output = stdout.getvalue()
        self.assertIn('Daemon instance 1: /tmp/demo/seiscat.conf', output)
        self.assertIn('Started at : 2026-04-24T09:00:00+00:00', output)
        self.assertIn('Status     : success', output)

    def test_status_hides_instances_when_no_service_installed(self):
        state = {
            'instance': {
                'tag': 'abcd1234',
                'config_file': '/tmp/demo/seiscat.conf',
                'db_file': '/tmp/demo/seiscat.sqlite',
                'state_file': '/tmp/demo/state.json',
                'lock_file': '/tmp/demo/daemon.lock',
            },
            'last_run': {
                'started_at': '2026-04-24T09:00:00+00:00',
                'status': 'success',
                'stages': {
                    'updatedb': {
                        'status': 'success',
                        'elapsed_s': 0.5,
                    }
                },
            },
        }
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            self._write_instance_files(tmp, state)
            stdout = io.StringIO()
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.services._systemd_unit_dir',
                    return_value=tmp,
                ),
                patch('seiscat.daemon.services._systemctl'),
                patch('seiscat.daemon.services.sys.platform', 'linux'),
                patch('sys.stdout', new=stdout),
            ):
                show_status({'args': object()})
        output = stdout.getvalue()
        self.assertNotIn('Daemon instance 1:', output)
        self.assertIn('No daemon run recorded yet.', output)


class TestUninstallService(unittest.TestCase):
    """Test uninstall-service behavior."""

    def test_uninstall_systemd_asks_choice_when_multiple(self):
        with tempfile.TemporaryDirectory() as d:
            unit_dir = pathlib.Path(d)
            timer1 = unit_dir / 'seiscat-daemon.timer'
            service1 = unit_dir / 'seiscat-daemon.service'
            timer2 = unit_dir / 'seiscat-daemon.abcd1234.timer'
            service2 = unit_dir / 'seiscat-daemon.abcd1234.service'
            timer1.write_text('', encoding='utf-8')
            service1.write_text('', encoding='utf-8')
            timer2.write_text('', encoding='utf-8')
            service2.write_text('', encoding='utf-8')

            with (
                patch(
                    'seiscat.daemon.services._systemd_unit_dir',
                    return_value=unit_dir,
                ),
                patch('seiscat.daemon.services.input', return_value='2'),
                patch('seiscat.daemon.services._systemctl') as mock_systemctl,
            ):
                _uninstall_systemd(system=False)

            self.assertFalse(timer1.exists())
            self.assertFalse(service1.exists())
            self.assertTrue(timer2.exists())
            self.assertTrue(service2.exists())
            mock_systemctl.assert_has_calls(
                [
                    call(
                        ['--user', 'disable', '--now', timer1.name],
                        check=False,
                    ),
                    call(
                        ['--user', 'disable', '--now', service1.name],
                        check=False,
                    ),
                    call(['--user', 'daemon-reload'], check=False),
                ]
            )

    def test_uninstall_systemd_removes_matching_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            unit_dir = tmp / 'units'
            state_dir = tmp / 'state'
            unit_dir.mkdir()
            state_dir.mkdir()

            timer = unit_dir / 'seiscat-daemon.timer'
            service = unit_dir / 'seiscat-daemon.service'
            timer.write_text('', encoding='utf-8')
            service.write_text(
                'ExecStart=/usr/bin/seiscat daemon -c /tmp/a.conf run\n',
                encoding='utf-8',
            )

            keep_registry = state_dir / 'daemon_instance.keep.json'
            keep_state = state_dir / 'daemon_state.keep.json'
            keep_lock = state_dir / 'daemon.keep.lock'
            keep_registry.write_text(
                json.dumps({
                    'tag': 'keep',
                    'config_file': '/tmp/b.conf',
                    'state_file': str(keep_state),
                    'lock_file': str(keep_lock),
                }),
                encoding='utf-8',
            )
            keep_state.write_text('{}', encoding='utf-8')
            keep_lock.write_text('{}', encoding='utf-8')

            del_registry = state_dir / 'daemon_instance.del.json'
            del_state = state_dir / 'daemon_state.del.json'
            del_lock = state_dir / 'daemon.del.lock'
            del_registry.write_text(
                json.dumps({
                    'tag': 'del',
                    'config_file': '/tmp/a.conf',
                    'state_file': str(del_state),
                    'lock_file': str(del_lock),
                }),
                encoding='utf-8',
            )
            del_state.write_text('{}', encoding='utf-8')
            del_lock.write_text('{}', encoding='utf-8')

            with (
                patch(
                    'seiscat.daemon.services._systemd_unit_dir',
                    return_value=unit_dir,
                ),
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=state_dir,
                ),
                patch('seiscat.daemon.services._systemctl'),
            ):
                _uninstall_systemd(system=False)

            self.assertTrue(keep_registry.exists())
            self.assertTrue(keep_state.exists())
            self.assertTrue(keep_lock.exists())
            self.assertFalse(del_registry.exists())
            self.assertFalse(del_state.exists())
            self.assertFalse(del_lock.exists())


if __name__ == '__main__':
    unittest.main()

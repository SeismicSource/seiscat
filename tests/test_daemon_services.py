# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for seiscat daemon service artifact generation."""

import pathlib
import unittest

from seiscat.daemon.services import (
    _LAUNCHD_LABEL,
    _SYSTEMD_SERVICE,
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


if __name__ == '__main__':
    unittest.main()

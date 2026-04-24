# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for seiscat daemon orchestration (daemon.py)."""

import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from seiscat.daemon.cycle import (
    _acquire_lock,
    _discover_instances,
    _instance_tag,
    _load_state,
    _pid_alive,
    _read_lock,
    _release_lock,
    _save_state,
    _write_lock,
    parse_interval_seconds,
    run_daemon_cycle,
)


# ---------------------------------------------------------------------------
# parse_interval_seconds
# ---------------------------------------------------------------------------

class TestParseIntervalSeconds(unittest.TestCase):
    """Test the interval-string parser."""

    def test_minutes(self):
        self.assertEqual(parse_interval_seconds('15 minutes'), 900)

    def test_minute_singular(self):
        self.assertEqual(parse_interval_seconds('1 minute'), 60)

    def test_hours(self):
        self.assertEqual(parse_interval_seconds('6 hours'), 21600)

    def test_hour_singular(self):
        self.assertEqual(parse_interval_seconds('1 hour'), 3600)

    def test_seconds(self):
        self.assertEqual(parse_interval_seconds('30 seconds'), 30)

    def test_days(self):
        self.assertEqual(parse_interval_seconds('2 days'), 172800)

    def test_case_insensitive(self):
        self.assertEqual(parse_interval_seconds('15 MINUTES'), 900)

    def test_bad_format_raises(self):
        with self.assertRaises(ValueError):
            parse_interval_seconds('15minutes')

    def test_bad_unit_raises(self):
        with self.assertRaises(ValueError):
            parse_interval_seconds('15 weeks')

    def test_non_integer_value_raises(self):
        with self.assertRaises(ValueError):
            parse_interval_seconds('1.5 hours')


# ---------------------------------------------------------------------------
# Lock helpers
# ---------------------------------------------------------------------------

class TestLockHelpers(unittest.TestCase):
    """Test lock read/write/acquire/release helpers."""

    def _make_config(self, tmp_path):
        """Return a minimal config dict pointing lock/state into tmp_path."""
        return {
            'db_file': '/tmp/test_seiscat.sqlite',
            'daemon_lock_timeout_seconds': 300,
            'daemon_state_file': str(tmp_path / 'state.json'),
            'daemon_log_file': None,
        }

    def test_write_and_read_lock(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            lock_path = Path(d) / 'daemon.lock'
            _write_lock(lock_path)
            pid, ts = _read_lock(lock_path)
            self.assertEqual(pid, os.getpid())
            self.assertAlmostEqual(ts, time.time(), delta=5)

    def test_read_lock_missing_returns_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            lock_path = Path(d) / 'daemon.lock'
            pid, ts = _read_lock(lock_path)
            self.assertIsNone(pid)
            self.assertIsNone(ts)

    def test_pid_alive_self(self):
        self.assertTrue(_pid_alive(os.getpid()))

    def test_pid_alive_nonexistent(self):
        # PID 0 is the kernel; sending signal 0 to it should raise
        # PermissionError on macOS/Linux; won't return True for a
        # "nonexistent" user process.
        # Use a known-dead PID instead: find one by trying very high PIDs.
        self.assertFalse(_pid_alive(9999999))

    def test_acquire_lock_first_time(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {
                'db_file': '/tmp/test_seiscat.sqlite',
                'daemon_lock_timeout_seconds': 300,
                'daemon_state_file': str(Path(d) / 'state.json'),
                'daemon_log_file': None,
            }
            with patch(
                'seiscat.daemon.cycle._default_state_dir',
                return_value=Path(d)
            ):
                result = _acquire_lock(config)
                self.assertTrue(result)

    def test_acquire_lock_live_process_returns_false(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {
                'db_file': '/tmp/test_seiscat.sqlite',
                'daemon_lock_timeout_seconds': 300,
                'daemon_state_file': str(Path(d) / 'state.json'),
                'daemon_log_file': None,
            }
            with patch(
                'seiscat.daemon.cycle._default_state_dir',
                return_value=Path(d)
            ):
                # Write lock with current PID (simulates live instance)
                lock_path = Path(d) / f'daemon.{_instance_tag(config)}.lock'
                _write_lock(lock_path)
                # Second acquire should return False
                result = _acquire_lock(config)
                self.assertFalse(result)

    def test_acquire_lock_stale_process_recovers(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {
                'db_file': '/tmp/test_seiscat.sqlite',
                'daemon_lock_timeout_seconds': 300,
                'daemon_state_file': str(Path(d) / 'state.json'),
                'daemon_log_file': None,
            }
            with patch(
                'seiscat.daemon.cycle._default_state_dir',
                return_value=Path(d)
            ):
                lock_path = Path(d) / f'daemon.{_instance_tag(config)}.lock'
                # Write lock with a dead PID
                lock_path.write_text(
                    json.dumps({'pid': 9999999, 'ts': time.time()}),
                    encoding='utf-8',
                )
                result = _acquire_lock(config)
                self.assertTrue(result)

    def test_release_lock_own_process(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {
                'db_file': '/tmp/test_seiscat.sqlite',
                'daemon_lock_timeout_seconds': 300,
                'daemon_state_file': str(Path(d) / 'state.json'),
                'daemon_log_file': None,
            }
            with patch(
                'seiscat.daemon.cycle._default_state_dir',
                return_value=Path(d)
            ):
                lock_path = Path(d) / f'daemon.{_instance_tag(config)}.lock'
                _write_lock(lock_path)
                self.assertTrue(lock_path.exists())
                _release_lock(config)
                self.assertFalse(lock_path.exists())


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestStatePersistence(unittest.TestCase):
    """Test state save/load round-trip."""

    def test_save_and_load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {'daemon_state_file': str(Path(d) / 'state.json')}
            state = {
                'last_run': {
                    'started_at': '2026-01-01T00:00:00+00:00',
                    'status': 'success',
                }
            }
            _save_state(config, state)
            loaded = _load_state(config)
            self.assertEqual(loaded, state)

    def test_load_missing_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config = {'daemon_state_file': str(Path(d) / 'state.json')}
            loaded = _load_state(config)
            self.assertEqual(loaded, {})

    def test_save_none_state_file_is_noop(self):
        config = {'daemon_state_file': None}
        # Should not raise
        _save_state(config, {'foo': 'bar'})

    def test_run_cycle_persists_instance_metadata_and_registry(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = {
                'db_file': str(tmp / 'seiscat.sqlite'),
                'daemon_jitter_seconds': 0,
                'daemon_lock_timeout_seconds': 300,
                'daemon_state_file': str(tmp / 'state.json'),
                'daemon_log_file': None,
                'daemon_run_fetch_event': False,
                'daemon_run_fetch_data': False,
                'args': MagicMock(configfile=str(tmp / 'seiscat.conf')),
            }
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch('seiscat.daemon.cycle._run_updatedb', return_value=0.5),
            ):
                run_daemon_cycle(config)
            state = _load_state(config)
            self.assertEqual(
                state['instance']['config_file'],
                os.path.abspath(str(tmp / 'seiscat.conf')),
            )
            self.assertEqual(
                state['instance']['db_file'],
                str(tmp / 'seiscat.sqlite'),
            )
            with patch(
                'seiscat.daemon.cycle._default_state_dir',
                return_value=tmp,
            ):
                instances = _discover_instances()
            self.assertEqual(len(instances), 1)
            self.assertEqual(
                instances[0]['config_file'],
                os.path.abspath(str(tmp / 'seiscat.conf')),
            )


# ---------------------------------------------------------------------------
# Cycle orchestration
# ---------------------------------------------------------------------------

class TestRunDaemonCycle(unittest.TestCase):
    """Test run_daemon_cycle stage ordering and flag handling."""

    def _make_config(self, tmp_path, fetch_event=False, fetch_data=False):
        return {
            'db_file': '/tmp/test_seiscat.sqlite',
            'daemon_jitter_seconds': 0,
            'daemon_lock_timeout_seconds': 300,
            'daemon_state_file': str(tmp_path / 'state.json'),
            'daemon_log_file': None,
            'daemon_run_fetch_event': fetch_event,
            'daemon_run_fetch_data': fetch_data,
            'args': MagicMock(),
        }

    def test_updatedb_only_cycle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = self._make_config(tmp)
            call_order = []
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.cycle._run_updatedb',
                    side_effect=lambda c: call_order.append('updatedb') or 0.1,
                ),
                patch(
                    'seiscat.daemon.cycle._run_fetch_event',
                    side_effect=lambda c: (
                        call_order.append('fetch_event') or 0.1),
                ),
                patch(
                    'seiscat.daemon.cycle._run_fetch_data',
                    side_effect=lambda c: (
                        call_order.append('fetch_data') or 0.1),
                ),
            ):
                run_daemon_cycle(config)
            self.assertEqual(call_order, ['updatedb'])

    def test_all_stages_cycle(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = self._make_config(tmp, fetch_event=True, fetch_data=True)
            call_order = []
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.cycle._run_updatedb',
                    side_effect=lambda c: call_order.append('updatedb') or 0.1,
                ),
                patch(
                    'seiscat.daemon.cycle._run_fetch_event',
                    side_effect=lambda c: (
                        call_order.append('fetch_event') or 0.1),
                ),
                patch(
                    'seiscat.daemon.cycle._run_fetch_data',
                    side_effect=lambda c: (
                        call_order.append('fetch_data') or 0.1),
                ),
            ):
                run_daemon_cycle(config)
            self.assertEqual(
                call_order,
                ['updatedb', 'fetch_event', 'fetch_data'],
            )

    def test_cycle_skipped_when_lock_held(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = self._make_config(tmp)
            # Write a lock held by the current process (simulates overlap)
            lock_path = tmp / f'daemon.{_instance_tag(config)}.lock'
            _write_lock(lock_path)
            updatedb_called = []
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.cycle._run_updatedb',
                    side_effect=lambda c: updatedb_called.append(True) or 0.1,
                ),
                self.assertRaises(SystemExit) as cm,
            ):
                run_daemon_cycle(config)
            self.assertEqual(cm.exception.code, 0)
            self.assertEqual(updatedb_called, [])

    def test_state_file_written_after_success(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = self._make_config(tmp)
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch('seiscat.daemon.cycle._run_updatedb', return_value=0.5),
            ):
                run_daemon_cycle(config)
            state = _load_state(config)
            self.assertIn('last_run', state)
            self.assertEqual(state['last_run']['status'], 'success')
            self.assertIn('updatedb', state['last_run']['stages'])

    def test_state_file_shows_failed_on_updatedb_exit(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            config = self._make_config(tmp)
            with (
                patch(
                    'seiscat.daemon.cycle._default_state_dir',
                    return_value=tmp,
                ),
                patch(
                    'seiscat.daemon.cycle._run_updatedb',
                    side_effect=SystemExit(1),
                ),
                self.assertRaises(SystemExit),
            ):
                run_daemon_cycle(config)
            state = _load_state(config)
            self.assertEqual(state['last_run']['status'], 'failed')


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for `seiscat daemon` CLI argument parsing."""

import unittest
from unittest.mock import patch

from seiscat.config.parse_arguments import parse_arguments


class TestDaemonParse(unittest.TestCase):
    """Test `seiscat daemon` parser tree."""

    # --- daemon run ---

    @patch('sys.argv', ['seiscat', 'daemon', 'run'])
    def test_daemon_run_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'daemon')
        self.assertEqual(args.daemon_action, 'run')

    @patch('sys.argv', ['seiscat', 'daemon', '-c', 'custom.conf', 'run'])
    def test_daemon_run_configfile(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'daemon')
        self.assertEqual(args.daemon_action, 'run')
        self.assertEqual(args.configfile, 'custom.conf')

    # --- daemon install-service ---

    @patch('sys.argv', ['seiscat', 'daemon', 'install-service'])
    def test_daemon_install_service_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'daemon')
        self.assertEqual(args.daemon_action, 'install-service')
        self.assertFalse(args.system)

    @patch('sys.argv', ['seiscat', 'daemon', 'install-service', '--system'])
    def test_daemon_install_service_system_flag(self):
        args = parse_arguments()
        self.assertEqual(args.daemon_action, 'install-service')
        self.assertTrue(args.system)

    # --- daemon uninstall-service ---

    @patch('sys.argv', ['seiscat', 'daemon', 'uninstall-service'])
    def test_daemon_uninstall_service_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'daemon')
        self.assertEqual(args.daemon_action, 'uninstall-service')
        self.assertFalse(args.system)

    @patch('sys.argv', ['seiscat', 'daemon', 'uninstall-service', '--system'])
    def test_daemon_uninstall_service_system_flag(self):
        args = parse_arguments()
        self.assertEqual(args.daemon_action, 'uninstall-service')
        self.assertTrue(args.system)

    # --- daemon status ---

    @patch('sys.argv', ['seiscat', 'daemon', 'status'])
    def test_daemon_status_parse(self):
        args = parse_arguments()
        self.assertEqual(args.action, 'daemon')
        self.assertEqual(args.daemon_action, 'status')

    # --- daemon without sub-action shows help ---

    @patch('sys.argv', ['seiscat', 'daemon'])
    def test_daemon_without_subcommand_shows_help(self):
        with self.assertRaises(SystemExit) as cm:
            parse_arguments()
        self.assertEqual(cm.exception.code, 0)

    @patch('seiscat.config.parse_arguments.platform.system',
           return_value='Windows')
    @patch('sys.argv', ['seiscat', '--help'])
    def test_daemon_not_shown_in_help_on_windows(self, _mock_platform):
        with patch('sys.stdout') as mock_stdout:
            with self.assertRaises(SystemExit):
                parse_arguments()
        printed = ''.join(
            call.args[0] for call in mock_stdout.write.call_args_list)
        self.assertNotIn('daemon', printed)

    @patch('seiscat.config.parse_arguments.platform.system',
           return_value='Windows')
    @patch('sys.argv', ['seiscat', 'daemon', 'status'])
    def test_daemon_command_unavailable_on_windows(self, _mock_platform):
        with self.assertRaises(SystemExit) as cm:
            parse_arguments()
        self.assertEqual(cm.exception.code, 2)


if __name__ == '__main__':
    unittest.main()

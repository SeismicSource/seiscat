# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for daemon dispatch behavior in main."""

import unittest
from argparse import Namespace
from unittest.mock import patch

from seiscat import main


class TestMainDaemonDispatch(unittest.TestCase):
    """Test daemon commands that must not require config loading."""

    @patch('seiscat.daemon.run_daemon_command')
    @patch('seiscat.config.read_config')
    @patch('seiscat.config.parse_configspec', return_value=object())
    @patch('seiscat.config.parse_arguments')
    def test_daemon_uninstall_service_skips_config_read(
        self,
        mock_parse_arguments,
        _mock_parse_configspec,
        mock_read_config,
        mock_run_daemon_command,
    ):
        args = Namespace(
            action='daemon',
            daemon_action='uninstall-service',
            configfile='missing.conf',
            system=False,
        )
        mock_parse_arguments.return_value = args

        with self.assertRaises(SystemExit) as cm:
            main.run()

        self.assertEqual(cm.exception.code, 0)
        mock_read_config.assert_not_called()
        mock_run_daemon_command.assert_called_once_with({'args': args})


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for clipboard fallback logic in pager."""

import unittest
from subprocess import CalledProcessError
from unittest.mock import mock_open, patch

from seiscat.print.pager import _copy_to_clipboard


class TestClipboardFallbacks(unittest.TestCase):
    """Test cross-platform clipboard fallback order."""

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    @patch('builtins.open', side_effect=OSError)
    def test_linux_falls_back_to_xsel_after_wlcopy_xclip(
            self, _mock_open, mock_run, _mock_system):
        """Linux should try wl-copy, then xclip, then xsel."""
        mock_run.side_effect = [
            FileNotFoundError(),
            FileNotFoundError(),
            None,
        ]

        success = _copy_to_clipboard('test-evid-123')
        attempts = [call.args[0][0] for call in mock_run.call_args_list]

        self.assertTrue(success)
        self.assertEqual(attempts, ['wl-copy', 'xclip', 'xsel'])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run')
    @patch(
        'builtins.open',
        new_callable=mock_open,
        read_data='Linux version ... Microsoft ...',
    )
    def test_wsl_uses_clip_exe_as_last_resort(
            self, _mock_open, mock_run, _mock_system):
        """WSL should fall back to clip.exe if Linux tools are unavailable."""
        mock_run.side_effect = [
            CalledProcessError(returncode=1, cmd='wl-copy'),
            CalledProcessError(returncode=1, cmd='xclip'),
            CalledProcessError(returncode=1, cmd='xsel'),
            None,
        ]

        success = _copy_to_clipboard('test-evid-123')
        attempts = [call.args[0][0] for call in mock_run.call_args_list]

        self.assertTrue(success)
        self.assertEqual(attempts, ['wl-copy', 'xclip', 'xsel', 'clip.exe'])

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=FileNotFoundError)
    @patch('builtins.open', side_effect=OSError)
    @patch('seiscat.print.pager._copy_with_iterm2', return_value=False)
    @patch('seiscat.print.pager._copy_with_osc52', return_value=False)
    def test_returns_false_when_all_commands_fail(
            self, _mock_osc52, _mock_iterm2, _mock_open,
            _mock_run, _mock_system):
        """Copy should fail cleanly when no clipboard command is available."""
        self.assertFalse(_copy_to_clipboard('test-evid-123'))

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=FileNotFoundError)
    @patch('builtins.open', side_effect=OSError)
    @patch('seiscat.print.pager._copy_with_iterm2', return_value=False)
    @patch('seiscat.print.pager._copy_with_osc52', return_value=True)
    def test_uses_osc52_when_linux_tools_fail(
            self, mock_osc52, mock_iterm2, _mock_open,
            _mock_run, _mock_system):
        """When Linux clipboard tools fail, OSC52 fallback should be used."""
        self.assertTrue(_copy_to_clipboard('test-evid-123'))
        mock_iterm2.assert_called_once_with('test-evid-123')
        mock_osc52.assert_called_once_with('test-evid-123')

    @patch('platform.system', return_value='Linux')
    @patch('subprocess.run', side_effect=FileNotFoundError)
    @patch('builtins.open', side_effect=OSError)
    @patch('seiscat.print.pager._copy_with_iterm2', return_value=True)
    @patch('seiscat.print.pager._copy_with_osc52', return_value=True)
    def test_uses_iterm2_before_osc52_when_available(
            self, mock_osc52, mock_iterm2, _mock_open,
            _mock_run, _mock_system):
        """iTerm2 fallback should short-circuit before OSC52."""
        self.assertTrue(_copy_to_clipboard('test-evid-123'))
        mock_iterm2.assert_called_once_with('test-evid-123')
        mock_osc52.assert_not_called()


if __name__ == '__main__':
    unittest.main()

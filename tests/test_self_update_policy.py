# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for self update policy decisions."""

import unittest
from unittest.mock import patch

from seiscat.self.install_detection import InstallContext
from seiscat.self.update import update_seiscat


class TestSelfUpdatePolicy(unittest.TestCase):
    """Validate release/git policy for `seiscat self update`."""

    @patch('seiscat.self.update.shutil.which', return_value='/usr/bin/uv')
    @patch('seiscat.self.update._uv_update_release')
    @patch('seiscat.self.update.detect_install_context')
    @patch(
        'seiscat.self.update.get_latest_release_version',
        return_value='0.9.2'
    )
    def test_git_install_switches_to_release_if_release_is_higher(
            self,
            _mock_latest,
            mock_detect,
            mock_uv_release,
            _mock_which):
        mock_detect.return_value = InstallContext(
            installer='uv',
            channel='git',
            version_installed='0.9.1',
            source_url='git+https://github.com/SeismicSource/seiscat.git',
            editable=False,
            confidence='high',
        )

        msg = update_seiscat(git=False)

        mock_uv_release.assert_called_once()
        self.assertIn('switched to release', msg)

    @patch('seiscat.self.update._pip_update_release')
    @patch('seiscat.self.update.detect_install_context')
    @patch(
        'seiscat.self.update.get_latest_release_version',
        return_value='0.9.1'
    )
    def test_git_install_keeps_git_if_release_not_higher(
            self,
            _mock_latest,
            mock_detect,
            mock_pip_release):
        mock_detect.return_value = InstallContext(
            installer='pip',
            channel='git',
            version_installed='0.9.2',
            source_url='git+https://github.com/SeismicSource/seiscat.git',
            editable=False,
            confidence='high',
        )

        msg = update_seiscat(git=False)

        mock_pip_release.assert_not_called()
        self.assertIn('newer or equal', msg)

    @patch('seiscat.self.update._pip_update_git')
    @patch('seiscat.self.update.detect_install_context')
    def test_update_git_flag_uses_git_track(self, mock_detect, mock_pip_git):
        mock_detect.return_value = InstallContext(
            installer='pip',
            channel='release',
            version_installed='0.9.1',
            source_url=None,
            editable=False,
            confidence='high',
        )

        msg = update_seiscat(git=True)

        mock_pip_git.assert_called_once()
        self.assertIn('git version', msg)

    @patch('seiscat.self.update.detect_install_context')
    def test_editable_install_no_auto_update(self, mock_detect):
        mock_detect.return_value = InstallContext(
            installer='pip',
            channel='editable',
            version_installed='0.9.1',
            source_url='file:///tmp/seiscat',
            editable=True,
            confidence='high',
        )

        msg = update_seiscat(git=False)
        self.assertIn('Editable install detected', msg)

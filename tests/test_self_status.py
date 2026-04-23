# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for `seiscat self status` reporting."""

import unittest
from io import StringIO
from unittest.mock import patch

from seiscat.self.install_detection import InstallContext
from seiscat.self.status import get_self_status, print_self_status


class TestSelfStatus(unittest.TestCase):
    """Validate optional plotting package reporting in self status."""

    @patch('seiscat.self.status.find_spec')
    @patch('seiscat.self.status.completion_status')
    @patch(
        'seiscat.self.status.get_latest_release_version',
        return_value='0.9.3'
    )
    @patch('seiscat.self.status.detect_install_context')
    def test_get_self_status_reports_optional_plotting_modules(
            self,
            mock_detect,
            _mock_latest,
            mock_completion,
            mock_find_spec):
        mock_detect.return_value = InstallContext(
            installer='uv',
            channel='release',
            version_installed='0.9.2',
            source_url=None,
            editable=False,
            confidence='high',
        )
        mock_completion.return_value = {
            'installed': True,
            'shell': 'zsh',
            'details': 'ok',
        }
        mock_find_spec.side_effect = lambda name: {
            'cartopy': object(),
            'plotly': object(),
            'pandas': None,
            'folium': None,
        }[name]

        status = get_self_status()

        self.assertEqual(
            status['optional_plotting_modules'],
            {
                'cartopy': True,
                'plotly': True,
                'pandas': False,
                'folium': False,
            }
        )

    @patch('seiscat.self.status.find_spec')
    @patch('seiscat.self.status.completion_status')
    @patch(
        'seiscat.self.status.get_latest_release_version',
        return_value='0.9.3'
    )
    @patch('seiscat.self.status.detect_install_context')
    @patch('sys.stdout', new_callable=StringIO)
    def test_print_self_status_includes_optional_plotting_modules_line(
            self,
            mock_stdout,
            mock_detect,
            _mock_latest,
            mock_completion,
            mock_find_spec):
        mock_detect.return_value = InstallContext(
            installer='pip',
            channel='release',
            version_installed='0.9.3',
            source_url=None,
            editable=False,
            confidence='high',
        )
        mock_completion.return_value = {
            'installed': False,
            'shell': 'bash',
            'details': 'missing',
        }
        mock_find_spec.side_effect = lambda name: {
            'cartopy': None,
            'plotly': object(),
            'pandas': object(),
            'folium': None,
        }[name]

        print_self_status()

        output = mock_stdout.getvalue()
        self.assertIn(
            (
                'Optional plotting modules: '
                'cartopy= ✗missing, plotly= ✓installed, '
                'pandas= ✓installed, folium= ✗missing'
            ),
            output,
        )


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Test config path resolution rules.
"""
import os
import pathlib
import tempfile
import unittest
from seiscat.config.config import parse_configspec, read_config


class TestConfigPathResolution(unittest.TestCase):
    """Test resolution of relative paths in config files."""

    def test_event_dir_resolved_wave_station_kept_relative(self):
        """event_dir is absolutized, waveform/station names remain relative."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = pathlib.Path(tmpdir) / 'seiscat.conf'
            cfg_path.write_text(
                '\n'.join([
                    'db_file = seiscat_db.sqlite',
                    'event_dir = events',
                    'waveform_dir = waveforms',
                    'station_dir = stations',
                ])
            )
            config = read_config(str(cfg_path), parse_configspec())
            self.assertEqual(
                config['event_dir'],
                os.path.join(tmpdir, 'events')
            )
            self.assertEqual(config['waveform_dir'], 'waveforms')
            self.assertEqual(config['station_dir'], 'stations')


if __name__ == '__main__':
    unittest.main()

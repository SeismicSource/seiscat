# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Unit tests for ObsPy events reader module.

:copyright:
    2021-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch
from obspy import Catalog, UTCDateTime
from obspy.core.event import Event, Origin, Magnitude
from seiscat.sources.obspy_events import read_catalog_from_obspy_events


def create_mock_config(filename):
    """Create a mock config object for testing.

    :param filename: event filename
    :type filename: str

    :return: mock config dictionary
    :rtype: dict
    """
    args = MagicMock()
    args.fromfile = [filename]
    return {'args': args}


class TestReadCatalogFromObspyEvents(unittest.TestCase):
    """Test read_catalog_from_obspy_events function."""

    def _create_quakeml_file(self, num_events=1, suffix='.xml'):
        """Create a valid QuakeML file using ObsPy.

        :param num_events: number of events to create
        :type num_events: int
        :param suffix: file extension
        :type suffix: str

        :return: path to created file
        :rtype: str
        """
        catalog = Catalog()
        for i in range(num_events):
            event = Event()
            origin = Origin()
            origin.time = UTCDateTime(f'2023-05-{15+i:02d}T{10+i:02d}:30:00')
            origin.latitude = 42.5 + i * 0.5
            origin.longitude = 13.2 + i * 0.8
            origin.depth = 10000.0 + i * 5000.0
            event.origins.append(origin)
            event.preferred_origin_id = origin.resource_id

            magnitude = Magnitude()
            magnitude.mag = 3.5 + i * 0.5
            magnitude.magnitude_type = 'Mw'
            event.magnitudes.append(magnitude)
            event.preferred_magnitude_id = magnitude.resource_id

            catalog.append(event)

        # Write using ObsPy to ensure valid format
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix=suffix
        )
        temp_file.close()
        catalog.write(temp_file.name, format='QUAKEML')
        return temp_file.name

    def test_reads_quakeml_file(self):
        """Test reading a QuakeML file."""
        filename = self._create_quakeml_file(num_events=1, suffix='.xml')

        try:
            config = create_mock_config(filename)

            with patch('builtins.print'):
                cat = read_catalog_from_obspy_events(config)

            self.assertIsInstance(cat, Catalog)
            self.assertEqual(len(cat), 1)
            self.assertEqual(cat[0].origins[0].latitude, 42.5)
            self.assertEqual(cat[0].origins[0].longitude, 13.2)
            self.assertEqual(cat[0].origins[0].depth, 10000.0)
        finally:
            os.unlink(filename)

    def test_reads_quakeml_with_quakeml_extension(self):
        """Test reading a QuakeML file with .quakeml extension."""
        filename = self._create_quakeml_file(num_events=1, suffix='.quakeml')

        try:
            config = create_mock_config(filename)

            with patch('builtins.print'):
                cat = read_catalog_from_obspy_events(config)

            self.assertIsInstance(cat, Catalog)
            self.assertEqual(len(cat), 1)
            self.assertEqual(cat[0].origins[0].latitude, 42.5)
        finally:
            os.unlink(filename)

    def test_raises_error_for_nonexistent_file(self):
        """Test raises FileNotFoundError for nonexistent file."""
        config = create_mock_config('/nonexistent/file.xml')

        with self.assertRaises(FileNotFoundError):
            read_catalog_from_obspy_events(config)

    def test_raises_error_for_invalid_xml(self):
        """Test raises ValueError for invalid XML."""
        invalid_xml = """<?xml version="1.0"?>
<invalid>
  <xml>structure</xml>
</invalid>
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.xml'
        ) as f:
            f.write(invalid_xml)
            filename = f.name

        try:
            config = create_mock_config(filename)

            with self.assertRaises(ValueError):
                read_catalog_from_obspy_events(config)
        finally:
            os.unlink(filename)

    def test_raises_error_for_invalid_format(self):
        """Test raises ValueError for unsupported format."""
        invalid_content = "This is not a valid event file format"
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.txt'
        ) as f:
            f.write(invalid_content)
            filename = f.name

        try:
            config = create_mock_config(filename)

            with self.assertRaises(ValueError):
                read_catalog_from_obspy_events(config)
        finally:
            os.unlink(filename)

    def test_reads_multiple_events(self):
        """Test reading QuakeML file with multiple events."""
        filename = self._create_quakeml_file(num_events=2, suffix='.xml')

        try:
            config = create_mock_config(filename)

            with patch('builtins.print'):
                cat = read_catalog_from_obspy_events(config)

            self.assertEqual(len(cat), 2)
            self.assertEqual(cat[0].origins[0].latitude, 42.5)
            self.assertEqual(cat[1].origins[0].latitude, 43.0)
        finally:
            os.unlink(filename)


if __name__ == '__main__':
    unittest.main()

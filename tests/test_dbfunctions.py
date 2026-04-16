# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Unit tests for database helper functions.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import unittest
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from obspy import Catalog, UTCDateTime
from obspy.core.event import Event, Origin, Magnitude
from seiscat.database.dbfunctions import _process_where_option
from seiscat.database.dbfunctions import (
    get_db_columns,
    add_column_to_db,
    delete_column_from_db,
    rename_column_in_db,
    write_catalog_to_db,
)
from seiscat.sources.csv import read_catalog_from_csv


class TestProcessWhereOption(unittest.TestCase):
    """Test translation of --where expressions to SQL placeholders."""

    def _assert_where_conversion(self, where_expr, expected_filter,
                                 expected_values):
        """Assert conversion result for a where expression."""
        where_filter, values = _process_where_option(where_expr)
        self.assertEqual(where_filter, expected_filter)
        self.assertEqual(values, expected_values)

    def test_translates_equal_none_to_is_null(self):
        """key = None or key == None should become IS NULL."""
        self._assert_where_conversion('mag==None', 'mag IS NULL', [])

    def test_translates_not_equal_none_to_is_not_null(self):
        """key != None should become IS NOT NULL."""
        self._assert_where_conversion('mag != None', 'mag IS NOT NULL', [])

    def test_keeps_regular_comparisons_parameterized(self):
        """Non-None values should still use placeholders and values."""
        self._assert_where_conversion(
            'depth < 10 AND mag >= 3', 'depth<? AND mag>=?', ['10', '3'])

    def test_mixed_none_and_regular_comparisons(self):
        """Mixed expressions should translate each part correctly."""
        self._assert_where_conversion(
            'mag==None OR depth>=5', 'mag IS NULL OR depth>=?', ['5'])


class TestSchemaColumnOperations(unittest.TestCase):
    """Test add/delete/rename column helpers."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tmpdir.name) / 'test.sqlite'
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            'CREATE TABLE events '
            '(evid TEXT, ver INTEGER, time TEXT, lat REAL, lon REAL, '
            'depth REAL, mag REAL, mag_type TEXT, event_type TEXT, '
            'PRIMARY KEY (evid, ver))'
        )
        conn.commit()
        conn.close()
        self.config = {
            'db_file': str(self.db_file),
            'args': SimpleNamespace(
                eventid=None,
                event_version=None,
                where=None,
                sortby='time',
                allversions=True,
                reverse=False,
            ),
        }

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_column(self):
        """Adding a column should extend the events table schema."""
        add_column_to_db(self.config, 'quality:TEXT')
        self.assertIn('quality', get_db_columns(self.config))

    def test_rename_custom_column(self):
        """A custom column can be renamed."""
        add_column_to_db(self.config, 'quality:TEXT')
        rename_column_in_db(self.config, 'quality=quality_flag')
        columns = get_db_columns(self.config)
        self.assertNotIn('quality', columns)
        self.assertIn('quality_flag', columns)

    def test_delete_custom_column(self):
        """A custom column can be deleted."""
        add_column_to_db(self.config, 'quality:TEXT')
        delete_column_from_db(self.config, 'quality')
        self.assertNotIn('quality', get_db_columns(self.config))

    def test_cannot_delete_default_column(self):
        """Default columns are protected from deletion."""
        with self.assertRaises(ValueError):
            delete_column_from_db(self.config, 'evid')

    def test_cannot_rename_default_column(self):
        """Default columns are protected from renaming."""
        with self.assertRaises(ValueError):
            rename_column_in_db(self.config, 'evid=event_id')


class TestInitDbCsvExtraColumns(unittest.TestCase):
    """Test creation of runtime CSV extra columns during initdb."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tmpdir.name) / 'test.sqlite'
        self.csv_file = Path(self.tmpdir.name) / 'events.csv'
        self.csv_file.write_text(
            'latitude,longitude,depth,magnitude,origin_time,quality,reviewer\n'
            '42.5,13.2,10.0,3.5,2023-05-15T14:30:45,A,alice\n',
            encoding='utf8'
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def _csv_config(self):
        args = MagicMock()
        args.fromfile = [str(self.csv_file)]
        args.depth_units = 'km'
        args.delimiter = ','
        args.column_names = None
        args.no_value = None
        args.csv_extra_columns = True
        args.action = 'initdb'
        return {'args': args}

    def _db_config(self, extra_columns):
        return {
            'db_file': str(self.db_file),
            'extra_field_names': None,
            'extra_field_types': None,
            'extra_field_defaults': None,
            '_csv_extra_columns': extra_columns,
            'overwrite_updated_events': False,
            'args': SimpleNamespace(
                eventid=None,
                event_version=None,
                where=None,
                sortby='time',
                allversions=True,
                reverse=False,
            ),
        }

    def test_initdb_creates_and_populates_extra_columns(self):
        """Runtime CSV extra columns should be added and filled."""
        with patch('builtins.print'):
            cat = read_catalog_from_csv(self._csv_config())
        config = self._db_config(
            getattr(cat, 'seiscat_extra_column_names', []))

        with patch('builtins.print'):
            write_catalog_to_db(cat, config, initdb=True)

        columns = get_db_columns(config)
        self.assertIn('quality', columns)
        self.assertIn('reviewer', columns)

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT quality, reviewer FROM events')
        row = cursor.fetchone()
        conn.close()
        self.assertEqual(row, ('A', 'alice'))


class TestEvidSimplificationConfig(unittest.TestCase):
    """Test keep_raw_evid behavior when writing events to DB."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_file = Path(self.tmpdir.name) / 'test.sqlite'

    def tearDown(self):
        self.tmpdir.cleanup()

    def _config(self, keep_raw_evid=False):
        return {
            'db_file': str(self.db_file),
            'extra_field_names': None,
            'extra_field_types': None,
            'extra_field_defaults': None,
            'overwrite_updated_events': False,
            'keep_raw_evid': keep_raw_evid,
            'args': SimpleNamespace(
                eventid=None,
                event_version=None,
                where=None,
                sortby='time',
                allversions=True,
                reverse=False,
            ),
        }

    @staticmethod
    def _catalog_with_url_like_resource_id():
        event = Event(
            resource_id=(
                'http://example.org/fdsnws/event/1/query?'
                'eventid=abc123&includeallorigins=true'
            )
        )
        origin = Origin(
            time=UTCDateTime('2024-01-01T00:00:00'),
            latitude=42.5,
            longitude=13.2,
            depth=10000.0,
        )
        event.origins.append(origin)
        event.preferred_origin_id = origin.resource_id
        magnitude = Magnitude(mag=3.4, magnitude_type='Mw')
        event.magnitudes.append(magnitude)
        event.preferred_magnitude_id = magnitude.resource_id
        return Catalog(events=[event])

    def _read_single_evid(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT evid FROM events')
        row = cursor.fetchone()
        conn.close()
        return row[0]

    def _write_single_event(self, keep_raw_evid):
        cat = self._catalog_with_url_like_resource_id()
        with patch('builtins.print'):
            write_catalog_to_db(
                cat,
                self._config(keep_raw_evid=keep_raw_evid),
                initdb=True,
            )

    def test_default_simplifies_evid_from_resource_id(self):
        """By default, evid is simplified from resource_id."""
        self._write_single_event(keep_raw_evid=False)
        self.assertEqual(self._read_single_evid(), 'abc123')

    def test_keep_raw_evid_preserves_full_resource_id(self):
        """When keep_raw_evid is True, the full resource_id is stored."""
        self._write_single_event(keep_raw_evid=True)
        self.assertEqual(
            self._read_single_evid(),
            (
                'http://example.org/fdsnws/event/1/query?'
                'eventid=abc123&includeallorigins=true'
            ),
        )


if __name__ == '__main__':
    unittest.main()

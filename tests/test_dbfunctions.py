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
from seiscat.database.dbfunctions import _process_where_option
from seiscat.database.dbfunctions import (
    get_db_columns,
    add_column_to_db,
    delete_column_from_db,
    rename_column_in_db,
)


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


if __name__ == '__main__':
    unittest.main()

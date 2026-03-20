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
from seiscat.database.dbfunctions import _process_where_option


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


if __name__ == '__main__':
    unittest.main()

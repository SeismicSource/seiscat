# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for seiscat.database.get_set."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from seiscat.database.get_set import seiscat_get


class TestSeiscatGet(unittest.TestCase):
    """Test seiscat_get behavior."""

    @patch('seiscat.database.get_set.read_fields_and_rows_from_db')
    @patch('seiscat.database.get_set.err_exit')
    @patch('builtins.print')
    def test_get_without_eventid_prints_all_values(
            self, mock_print, mock_err_exit, mock_read_fields):
        """If eventid is omitted, all matching values are printed."""
        mock_read_fields.return_value = (
            ['mag'],
            [(1.1,), (2.2,), (3.3,)]
        )

        config = {
            'args': SimpleNamespace(
                key='mag',
                eventid=None,
                event_version=None
            )
        }

        seiscat_get(config)

        mock_err_exit.assert_not_called()
        self.assertEqual(mock_print.call_count, 3)
        mock_print.assert_any_call(1.1)
        mock_print.assert_any_call(2.2)
        mock_print.assert_any_call(3.3)

    @patch('seiscat.database.get_set.read_fields_and_rows_from_db')
    @patch('seiscat.database.get_set.err_exit')
    def test_get_with_no_rows_exits(self, mock_err_exit, mock_read_fields):
        """Missing events still trigger an error exit."""
        mock_read_fields.return_value = (['mag'], [])

        config = {
            'args': SimpleNamespace(
                key='mag',
                eventid=None,
                event_version=None
            )
        }

        seiscat_get(config)

        mock_err_exit.assert_called_once_with('Event not found')

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for seiscat.database.editdb column-operation behavior."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from seiscat.database.editdb import _edit_columns


class TestEditDbProtectedColumns(unittest.TestCase):
    """Protected columns should fail before confirmation prompts."""

    @patch('seiscat.database.editdb.rename_column_in_db')
    @patch('seiscat.database.editdb._are_you_sure')
    @patch('seiscat.database.editdb.err_exit')
    def test_protected_rename_does_not_ask_confirmation(
            self, mock_err_exit, mock_are_you_sure, mock_rename):
        """Renaming protected columns should error without prompting."""
        mock_err_exit.side_effect = SystemExit(1)
        args = SimpleNamespace(
            eventid=None,
            event_version=None,
            where=None,
            add_column=None,
            delete_column=None,
            rename_column='evid=new_evid',
            force=False,
        )

        with self.assertRaises(SystemExit):
            _edit_columns({}, args)

        mock_are_you_sure.assert_not_called()
        mock_rename.assert_not_called()

    @patch('seiscat.database.editdb.delete_column_from_db')
    @patch('seiscat.database.editdb._are_you_sure')
    @patch('seiscat.database.editdb.err_exit')
    def test_protected_delete_does_not_ask_confirmation(
            self, mock_err_exit, mock_are_you_sure, mock_delete):
        """Deleting protected columns should error without prompting."""
        mock_err_exit.side_effect = SystemExit(1)
        args = SimpleNamespace(
            eventid=None,
            event_version=None,
            where=None,
            add_column=None,
            delete_column='evid',
            rename_column=None,
            force=False,
        )

        with self.assertRaises(SystemExit):
            _edit_columns({}, args)

        mock_are_you_sure.assert_not_called()
        mock_delete.assert_not_called()

    @patch('seiscat.database.editdb.rename_column_in_db')
    @patch('seiscat.database.editdb._are_you_sure')
    @patch('seiscat.database.editdb.err_exit')
    def test_invalid_rename_syntax_does_not_ask_confirmation(
            self, mock_err_exit, mock_are_you_sure, mock_rename):
        """Invalid rename syntax should fail before confirmation prompt."""
        mock_err_exit.side_effect = SystemExit(1)
        args = SimpleNamespace(
            eventid=None,
            event_version=None,
            where=None,
            add_column=None,
            delete_column=None,
            rename_column='mycol',
            force=False,
        )

        with self.assertRaises(SystemExit):
            _edit_columns({}, args)

        mock_are_you_sure.assert_not_called()
        mock_rename.assert_not_called()


if __name__ == '__main__':
    unittest.main()

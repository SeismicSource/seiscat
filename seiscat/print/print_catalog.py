# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Print the catalog.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
from ..utils import err_exit
# Other modules are lazily imported inside functions to speed up startup time
# pylint: disable=import-outside-toplevel


def _print_catalog_stats(config):
    """
    Print catalog statistics.

    :param config: config object
    """
    from ..database.dbfunctions import get_catalog_stats
    print(get_catalog_stats(config))


def _print_table_rows(header, body_rows):
    """
    Print table header and rows.

    :param header: header row string
    :param body_rows: list of body row strings
    """
    print(header)
    for row in body_rows:
        print(row)


def _display_table(header, body_rows):
    """
    Display table header and rows.

    Uses interactive curses pager if output is to a terminal,
    otherwise prints plain text.

    :param header: header row string
    :param body_rows: list of body row strings
    """
    # Check if output is to a terminal
    if sys.stdout.isatty():
        # Use curses pager with fixed header for terminal output
        from .pager import display_table_pager, PagerException
        try:
            display_table_pager(header, body_rows)
        except PagerException:
            # Fallback to simple print if curses fails
            _print_table_rows(header, body_rows)
    else:
        # Plain text output for pipes/files
        _print_table_rows(header, body_rows)


def _print_catalog_table(config):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    from ..database.dbfunctions import read_fields_and_rows_from_db
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # Build plain text table
    max_len = [len(f) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            max_len[i] = max(max_len[i], len(str(val)))
    # Build header
    header = '  '.join(f'{f:{max_len[i]}}' for i, f in enumerate(fields))
    # Build body rows
    body_rows = []
    for row in rows:
        row_str = '  '.join(
            f'{("None" if val is None else str(val)):{max_len[i]}}'
            for i, val in enumerate(row)
        )
        body_rows.append(row_str)
    # Display table (pager if TTY, plain text otherwise)
    _display_table(header, body_rows)


def print_catalog(config):
    """
    Print catalog.

    :param config: config object
    """
    args = config['args']
    try:
        if args.format == 'stats':
            _print_catalog_stats(config)
        elif args.format == 'table':
            _print_catalog_table(config)
        else:
            err_exit(f'Unknown format "{args.format}"')
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

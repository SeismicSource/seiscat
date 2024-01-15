# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Printing functions for seiscat.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .db import read_fields_and_rows_from_db, get_catalog_stats
from .utils import err_exit


def _print_catalog_stats(config):
    """
    Print catalog statistics.

    :param config: config object
    """
    print(get_catalog_stats(config))


def _print_catalog_table(config, eventid=None, version=None):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    fields, rows = read_fields_and_rows_from_db(config, eventid, version)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # get max length of each field
    max_len = [len(f) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            max_len[i] = max(max_len[i], len(str(val)))
    # print header
    for i, f in enumerate(fields):
        print(f'{f:{max_len[i]}}', end=' ')
    print()
    # print rows sorted by time and version
    time_idx = fields.index('time')
    ver_idx = fields.index('ver')
    reverse = config['args'].reverse
    for row in sorted(
            rows, key=lambda r: (r[time_idx], r[ver_idx]), reverse=reverse):
        for i, val in enumerate(row):
            val = 'None' if val is None else val
            print(f'{val:{max_len[i]}}', end=' ')
        print()


def _print_catalog_csv(config, eventid=None, version=None):
    """
    Print catalog as CSV.

    :param config: config object
    """
    fields, rows = read_fields_and_rows_from_db(config, eventid, version)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # print header
    print(','.join(fields))
    # print rows sorted by time and version
    time_idx = fields.index('time')
    ver_idx = fields.index('ver')
    reverse = config['args'].reverse
    for row in sorted(
            rows, key=lambda r: (r[time_idx], r[ver_idx]), reverse=reverse):
        print(','.join([str(val) for val in row]))


def print_catalog(config):
    """
    Print catalog.

    :param config: config object
    """
    args = config['args']
    if args.format == 'stats':
        _print_catalog_stats(config)
    elif args.format == 'table':
        _print_catalog_table(config, eventid=args.eventid)
    elif args.format == 'csv':
        _print_catalog_csv(config, eventid=args.eventid)
    else:
        err_exit(f'Unknown format "{args.format}"')

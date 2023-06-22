# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Printing functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .db import read_fields_and_rows_from_db, get_catalog_stats
from .utils import err_exit


def print_catalog_stats(config):
    """
    Print catalog statistics.

    :param config: config object
    """
    print(get_catalog_stats(config))


def print_catalog_table(config):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # get max length of each field
    max_len = [len(f[1]) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            max_len[i] = max(max_len[i], len(str(val)))
    # print header
    for i, f in enumerate(fields):
        print(f'{f[1]:{max_len[i]}}', end=' ')
    print()
    # print rows
    reverse = config['args'].reverse
    # sort by time (field 2) and version (field 1)
    for row in sorted(rows, key=lambda r: (r[2], r[1]), reverse=reverse):
        for i, val in enumerate(row):
            val = 'None' if val is None else val
            print(f'{val:{max_len[i]}}', end=' ')
        print()


def print_catalog(config):
    """
    Print catalog.

    :param config: config object
    """
    if config['args'].format == 'stats':
        print_catalog_stats(config)
    elif config['args'].format == 'table':
        print_catalog_table(config)
    else:
        err_exit(f'Unknown format "{config["args"].format}"')

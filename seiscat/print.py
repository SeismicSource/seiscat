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
import sqlite3
from .utils import err_exit


def print_catalog(config):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    db_file = config.get('db_file', None)
    if db_file is None:
        err_exit('db_file not set in config file')
    try:
        open(db_file, 'r')
    except FileNotFoundError:
        err_exit(f'Database file "{db_file}" not found.')
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    # get fields
    c.execute('PRAGMA table_info(events)')
    fields = c.fetchall()
    c.execute('SELECT * FROM events')
    rows = c.fetchall()
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
    for row in rows:
        for i, val in enumerate(row):
            val = 'None' if val is None else val
            print(f'{val:{max_len[i]}}', end=' ')
        print()
    conn.close()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Feed the database with events from a file or FDSN web services.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .dbfunctions import check_db_exists, write_catalog_to_db
from ..sources.fdsnws import open_fdsn_connection, query_events
from ..sources.csv import read_catalog_from_csv
from ..utils import ExceptionExit


def feeddb(config, initdb):
    """
    Feed the database with events from CSV file or FDSN web services.

    :param config: config object
    :param initdb: if True, create new database file
    """
    with ExceptionExit():
        check_db_exists(config, initdb)
    args = config['args']
    if args.fromfile:
        with ExceptionExit(additional_msg='Error reading CSV file'):
            cat = read_catalog_from_csv(
                args.fromfile, args.delimiter, args.column_names,
                args.depth_units)
    else:
        with ExceptionExit(additional_msg='Error connecting to FDSN server'):
            client = open_fdsn_connection(config)
        with ExceptionExit(additional_msg='Error querying FDSN server'):
            cat = query_events(client, config, first_query=initdb)
    with ExceptionExit(additional_msg='Error writing to database'):
        write_catalog_to_db(cat, config, initdb)

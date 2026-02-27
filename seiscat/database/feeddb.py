# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Feed the database with events from a file or FDSN web services.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .dbfunctions import check_db_exists, write_catalog_to_db
from ..sources.fdsnws import open_fdsn_connection, query_events
from ..sources.obspy_events import read_catalog_from_obspy_events
from ..sources.csv import read_catalog_from_csv
from ..utils import ExceptionExit, err_exit


def feeddb(config, initdb):
    """
    Feed the database with events from file(s) (CSV or any ObsPy-supported
    format) or FDSN web services.

    Multiple files can be provided with --fromfile and will be merged into
    a single catalog before writing to the database.

    :param config: config object
    :param initdb: if True, create new database file
    """
    with ExceptionExit():
        check_db_exists(config, initdb)
    args = config['args']
    if args.fromfile:
        # Handle multiple files (args.fromfile is always a list with nargs='+')
        cat = None
        for filename in args.fromfile:
            print(f'Reading event file: {filename}')
            # Try CSV first, then fall back to ObsPy
            try:
                file_cat = read_catalog_from_csv(config, filename)
            except FileNotFoundError:
                err_exit(f'File not found: {filename}')
            except ValueError as csv_error:
                # CSV reader failed, try ObsPy
                print(
                    '\nCSV reader could not read the file:\n'
                    f'{csv_error}\n\n'
                    f'Trying ObsPy reader...'
                )
                with ExceptionExit():
                    file_cat = read_catalog_from_obspy_events(config, filename)
            # Merge catalogs
            if cat is None:
                cat = file_cat
            else:
                cat.extend(file_cat)
    else:
        with ExceptionExit(additional_msg='Error connecting to FDSN server'):
            client = open_fdsn_connection(config)
        with ExceptionExit(additional_msg='Error querying FDSN server'):
            cat = query_events(client, config, first_query=initdb)
    with ExceptionExit(additional_msg='Error writing to database'):
        write_catalog_to_db(cat, config, initdb)

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


def _feed_from_file(config):
    """
    Read and merge events from multiple files.

    :param config: config object
    :return: merged ObsPy catalog or None if no files could be read
    """
    args = config['args']
    cat = None
    failed_files = []
    for filename in args.fromfile:
        print(f'Reading event file: {filename}')
        # Try CSV first, then fall back to ObsPy
        csv_error = None
        try:
            file_cat = read_catalog_from_csv(config, filename)
        except FileNotFoundError:
            err_exit(f'File not found: {filename}')
        except ValueError as e:
            # CSV reader failed, save the error and try ObsPy
            csv_error = e
            try:
                file_cat = read_catalog_from_obspy_events(config, filename)
            except ValueError as obspy_error:
                # Both readers failed, skip this file and continue
                failed_files.append((filename, csv_error, obspy_error))
                continue
        # Merge catalogs
        if cat is None:
            cat = file_cat
        else:
            cat.extend(file_cat)
    # Print errors for files that couldn't be read
    if failed_files:
        print('\nWarning: The following files could not be read:')
        for filename, csv_err, obspy_err in failed_files:
            print(f'\n  {filename}:')
            print(f'    CSV reader: {csv_err}')
            print(f'    ObsPy reader: {obspy_err}')
    # Check if at least one file was successfully read
    if cat is None:
        err_exit('Could not read any event files')
    return cat


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
        cat = _feed_from_file(config)
    else:
        with ExceptionExit(additional_msg='Error connecting to FDSN server'):
            client = open_fdsn_connection(config)
        with ExceptionExit(additional_msg='Error querying FDSN server'):
            cat = query_events(client, config, first_query=initdb)
    with ExceptionExit(additional_msg='Error writing to database'):
        write_catalog_to_db(cat, config, initdb)

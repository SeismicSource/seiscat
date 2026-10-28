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
from .cropdb import filter_catalog_by_config
from ..sources.fdsnws import open_fdsn_connection, query_events
from ..sources.obspy_events import read_catalog_from_obspy_events
from ..sources.csv import read_catalog_from_csv
from ..sources.jma import is_jma_hypocenter_file, read_catalog_from_jma
from ..utils import ExceptionExit, err_exit


def _read_catalog_from_file(config, filename):
    """
    Read a catalog from a file, auto-detecting its format.

    The JMA hypocenter format is recognized by its fixed-width records.
    Otherwise, the CSV reader is tried first, and the ObsPy reader is used
    as a fallback.

    :param config: config object
    :param filename: name of the file to read

    :return: a tuple with the catalog, the name of the reader that was
        tried first, and the exception raised by that reader (if any)
    :rtype: tuple(obspy.Catalog, str, Exception or None)
    """
    if is_jma_hypocenter_file(filename):
        reader_name = 'JMA'
        reader = read_catalog_from_jma
    else:
        reader_name = 'CSV'
        reader = read_catalog_from_csv
    try:
        return reader(config, filename), reader_name, None
    except ValueError as e:
        return None, reader_name, e


def _feed_from_file(config, initdb=False):
    """
    Read and merge events from multiple files.

    :param config: config object
    :return: merged ObsPy catalog or None if no files could be read
    """
    args = config['args']
    cat = None
    failed_files = []
    csv_extra_columns = []
    for filename in args.fromfile:
        print(f'Reading event file: {filename}')
        try:
            file_cat, reader_name, reader_error =\
                _read_catalog_from_file(config, filename)
        except FileNotFoundError:
            err_exit(f'File not found: {filename}')
        if file_cat is None:
            # the first reader failed, fall back to ObsPy
            try:
                file_cat = read_catalog_from_obspy_events(config, filename)
            except ValueError as obspy_error:
                # both readers failed, skip this file and continue
                failed_files.append(
                    (filename, reader_name, reader_error, obspy_error))
                continue
        # Collect extra CSV columns discovered by the CSV reader.
        for col in getattr(file_cat, 'seiscat_extra_column_names', []):
            if col not in csv_extra_columns:
                csv_extra_columns.append(col)
        # Merge catalogs
        if cat is None:
            cat = file_cat
        else:
            cat.extend(file_cat)
    # Print errors for files that couldn't be read
    if failed_files:
        print('\nWarning: The following files could not be read:')
        for filename, reader_name, reader_err, obspy_err in failed_files:
            print(f'\n  {filename}:')
            print(f'    {reader_name} reader: {reader_err}')
            print(f'    ObsPy reader: {obspy_err}')
    # Check if at least one file was successfully read
    if cat is None:
        err_exit('Could not read any event files')
    if initdb and getattr(args, 'csv_extra_columns', False):
        setattr(cat, 'seiscat_extra_column_names', csv_extra_columns)
    return cat


def feeddb(config, initdb):
    """
    Feed the database with events from file(s) or FDSN web services.

    Supported file formats are the JMA hypocenter format, CSV, and any
    ObsPy-supported format.

    Multiple files can be provided with --fromfile and will be merged into
    a single catalog before writing to the database.

    :param config: config object
    :param initdb: if True, create new database file
    """
    with ExceptionExit():
        check_db_exists(config, initdb)
    args = config['args']
    if args.fromfile:
        cat = _feed_from_file(config, initdb=initdb)
        if getattr(args, 'crop', False):
            cat = filter_catalog_by_config(cat, config)
    else:
        with ExceptionExit(additional_msg='Error connecting to FDSN server'):
            client = open_fdsn_connection(config)
        with ExceptionExit(additional_msg='Error querying FDSN server'):
            cat = query_events(client, config, first_query=initdb)
    with ExceptionExit(additional_msg='Error writing to database'):
        if initdb and getattr(args, 'csv_extra_columns', False):
            config['_csv_extra_columns'] = getattr(
                cat, 'seiscat_extra_column_names', [])
        write_catalog_to_db(cat, config, initdb)

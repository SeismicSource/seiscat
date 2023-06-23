# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Database functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import sqlite3
import numpy as np
from obspy import UTCDateTime
from .utils import err_exit

# Current supported DB version
# Increment this number when changing the DB schema
DB_VERSION = 1


def _check_db_version(cursor, config):
    """
    Check if database version is compatible with current version.

    :param cursor: database cursor
    :param config: config object
    """
    db_version = cursor.execute('PRAGMA user_version').fetchone()[0]
    db_file = config['db_file']
    if db_version < DB_VERSION:
        msg = (
            f'"{db_file}" has an old database version: '
            f'"{db_version}" Current supported version is "{DB_VERSION}".\n'
            'Remove or rename your old database file, '
            'so that a new one can be created.'
        )
        err_exit(msg)


def _set_db_version(cursor):
    """
    Set the database version.

    :param cursor: database cursor
    """
    cursor.execute('PRAGMA user_version = {v:d}'.format(v=DB_VERSION))


def check_db_exists(config, initdb):
    """
    Check if database file exists.

    :param config: config object
    :param initdb: if True, create new database file
    """
    db_file = config.get('db_file', None)
    if db_file is None:
        err_exit('db_file not set in config file')
    if initdb and os.path.exists(db_file):
        ans = input(
            f'"{db_file}" already exists. '
            'Do you want to overwrite it?\n'
            f'(Current database will be saved as "{db_file}.bak") [y/N] '
        )
        if ans not in ['y', 'Y']:
            err_exit('No database file created. Exiting.')
        else:
            os.rename(
                db_file, f'{db_file}.bak')
            print(
                f'Backup of "{db_file}" saved to '
                f'"{db_file}.bak"')
    if not initdb and not os.path.exists(db_file):
        err_exit(
            f'Database file "{db_file}" does not exist.\n'
            'Run "seiscat initdb" first.'
        )


def _same_values(event1, event2, skip_begin=0, skip_end=0):
    """
    Check if two events have the same values.

    :param event1: first event
    :param event2: second event
    :param skip_begin: number of fields to skip at the beginning
    :param skip_end: number of fields to skip at the end
    :returns: True if events have the same values, False otherwise
    """
    for idx in range(skip_begin, len(event1)-skip_end):
        try:
            # Use np.isclose() for numbers
            match = np.isclose(event1[idx], event2[idx])
        except TypeError:
            # Use == for strings
            match = event1[idx] == event2[idx]
        if not match:
            return False
    return True


def _get_evid(resource_id):
    """
    Get evid from resource_id.

    :param resource_id: resource_id string
    :returns: evid string
    """
    evid = resource_id
    if '/' in evid:
        evid = resource_id.split('/')[-1]
    if '?' in evid:
        evid = resource_id.split('?')[-1]
    if '&' in evid:
        evid = evid.split('&')[0]
    if '=' in evid:
        evid = evid.split('=')[-1]
    return evid


def _get_db_field_definitions(config):
    """
    Get a list of database fields.

    :param config: config object
    :returns: list of field definitions, number of extra fields
    """
    field_definitions = [
        'evid TEXT',
        'ver INTEGER',
        'time TEXT',
        'lat REAL',
        'lon REAL',
        'depth REAL',
        'mag REAL',
        'mag_type TEXT',
        'event_type TEXT',
    ]
    extra_field_names = config['extra_field_names'] or []
    extra_field_types = config['extra_field_types'] or []
    n_extra_fields = len(extra_field_names)
    field_definitions.extend(
        f'{name} {dbtype}' for name, dbtype
        in zip(extra_field_names, extra_field_types))
    return field_definitions, n_extra_fields


def _get_db_values_from_event(ev, config):
    """
    Get a list of values from an obspy event object.

    :param ev: obspy event object
    :param config: config object
    :returns: list of values
    """
    evid = _get_evid(str(ev.resource_id.id))
    version = 1
    orig = ev.preferred_origin() or ev.origins[0]
    time = str(orig.time)
    lat = orig.latitude
    lon = orig.longitude
    depth = orig.depth / 1e3  # km
    magntiude = ev.preferred_magnitude() or ev.magnitudes[0]
    mag = magntiude.mag
    mag_type = magntiude.magnitude_type
    event_type = ev.event_type
    values = [
        evid, version, time, lat, lon, depth, mag, mag_type, event_type]
    # add extra fields
    extra_field_defaults = config['extra_field_defaults'] or []
    values += extra_field_defaults
    return values


def write_catalog_to_db(cat, config, initdb):
    """
    Write catalog to database.

    :param cat: obspy Catalog object
    :param config: config object
    :param initdb: if True, create new database file
    """
    # open database connection
    conn = sqlite3.connect(config['db_file'])
    c = conn.cursor()
    if initdb:
        _set_db_version(c)
    else:
        _check_db_version(c, config)
    field_definitions, n_extra_fields = _get_db_field_definitions(config)
    # create table if it doesn't exist, use evid and ver as primary key
    c.execute(
        'CREATE TABLE IF NOT EXISTS events '
        f'({", ".join(field_definitions)}, PRIMARY KEY (evid, ver))')
    events_written = 0
    for ev in cat:
        values = _get_db_values_from_event(ev, config)
        if initdb or config['overwrite_updated_events']:
            # add events to table, replace events that already exist
            c.execute(
                'INSERT OR REPLACE INTO events VALUES '
                f'({", ".join("?" * len(values))})', values)
        else:
            # check if an event with the same values already exists
            evid = values[0]
            c.execute(
                'SELECT * FROM events WHERE evid = ?', (evid,))
            rows = c.fetchall()
            # check for different values, ignore evid and ver and extra fields
            rows_with_different_values = [
                row for row in rows
                if not _same_values(
                    values, row, skip_begin=2, skip_end=n_extra_fields)]
            try:
                max_version = max(row[1] for row in rows_with_different_values)
            except ValueError:
                # rows_with_different_values is empty
                max_version = 0
            values[1] = max_version + 1
            # add events to table, ignore events that have the same primary
            # keys (i.e., the same evid and ver)
            c.execute(
                'INSERT OR IGNORE INTO events VALUES '
                f'({", ".join("?" * len(values))})', values)
        events_written += c.rowcount
    # close database connection
    conn.commit()
    print(f'Wrote {events_written} events to database "{config["db_file"]}"')


def read_fields_and_rows_from_db(config, eventid=None, version=None):
    """
    Read fields and rows from database. Return a list of fields and a list of
    rows.

    :param config: config object
    :param eventid: limit to events with this evid
    :param version: limit to events with this version
                    (ignored if eventid is None)
    :returns: list of fields, list of rows
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
    # read field names
    c.execute('PRAGMA table_info(events)')
    # we just need the field names, which are in the second column
    fields = [f[1] for f in c.fetchall()]
    # read events
    if eventid is not None and version is not None:
        c.execute(
            'SELECT * FROM events WHERE evid = ? AND ver = ?',
            (eventid, version))
    elif eventid is not None:
        c.execute('SELECT * FROM events WHERE evid = ?', (eventid,))
    else:
        c.execute('SELECT * FROM events')
    try:
        allversions = config['args'].allversions
    except AttributeError:
        allversions = True
    rows = c.fetchall()
    if not allversions:
        # keep only the latest version of each event
        evids = set()
        rows_to_keep = []
        for row in sorted(rows, key=lambda r: r[:2], reverse=True):
            evid = row[0]
            if evid not in evids:
                rows_to_keep.append(row)
                evids.add(evid)
        rows = rows_to_keep
    conn.close()
    return fields, rows


def read_events_from_db(config):
    """
    Read events from database. Return a list of events.

    :param config: config object
    :returns: list of events, each event is a dictionary
    """
    fields, rows = read_fields_and_rows_from_db(config)
    # create a list of dictionaries
    events_list = []
    for event in rows:
        event_dict = dict(zip(fields, event))
        event_dict['time'] = UTCDateTime(event_dict['time'])
        events_list.append(event_dict)
    return events_list


def get_catalog_stats(config):
    """
    Get a string with catalog statistics.

    :param config: config object
    :returns: string with catalog statistics
    """
    events = read_events_from_db(config)
    nevents = len(events)
    tmin = min(event['time'] for event in events)
    tmax = max(event['time'] for event in events)
    tmin = tmin.strftime('%Y-%m-%dT%H:%M:%S')
    tmax = tmax.strftime('%Y-%m-%dT%H:%M:%S')
    mag_min = min(event['mag'] for event in events)
    mag_max = max(event['mag'] for event in events)
    return (
        f'{nevents} events from {tmin} to {tmax}\n'
        f'Magnitude range: {mag_min:.1f} - {mag_max:.1f}'
    )

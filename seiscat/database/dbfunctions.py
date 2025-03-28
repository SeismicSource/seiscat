# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Database functions for seiscat.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import re
import sqlite3
import numpy as np
from .data_types import Event, EventList

# Current supported DB version
# Increment this number when changing the DB schema
DB_VERSION = 1


def _get_db_connection(config, initdb=False):
    """
    Get database connection.

    :param config: config object
    :return: database connection

    :raises ValueError: if db_file is not set in config file
    :raises FileNotFoundError: if database file does not exist
    """
    db_file = config.get('db_file', None)
    if db_file is None:
        raise ValueError('db_file not set in config file')
    if not initdb:
        try:
            open(db_file, 'r', encoding='utf8')
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f'Database file "{db_file}" not found.') from e
    return sqlite3.connect(db_file)


def _check_db_version(cursor, config):
    """
    Check if database version is compatible with current version.

    :param cursor: database cursor
    :param config: config object

    :raises ValueError: if db_file version is not supported
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
        raise ValueError(msg)


def _set_db_version(cursor):
    """
    Set the database version.

    :param cursor: database cursor
    """
    cursor.execute(f'PRAGMA user_version = {DB_VERSION:d}')


def check_db_exists(config, initdb):
    """
    Check if database file exists.

    :param config: config object
    :param initdb: if True, create new database file

    :raises ValueError: if db_file is not set in config file
    :raises RuntimeError: if user does not want to overwrite existing database
    :raises FileNotFoundError: if database file does not exist
    """
    db_file = config.get('db_file', None)
    if db_file is None:
        raise ValueError('db_file not set in config file')
    if initdb and os.path.exists(db_file):
        ans = input(
            f'"{db_file}" already exists. '
            'Do you want to overwrite it?\n'
            f'(Current database will be saved as "{db_file}.bak") [y/N] '
        )
        if ans not in ['y', 'Y']:
            raise RuntimeError(
                'Existing database file will not be overwritten. Exiting.')
        os.rename(
            db_file, f'{db_file}.bak')
        print(
            f'Backup of "{db_file}" saved to '
            f'"{db_file}.bak"')
    if not initdb and not os.path.exists(db_file):
        raise FileNotFoundError(
            f'Database file "{db_file}" does not exist.\n'
            'Run "seiscat initdb" first.'
        )


def _same_values(values1, values2, skip_begin=0, skip_end=0):
    """
    Check if two lists of values have the same values.

    :param event1: first event
    :param event2: second event
    :param skip_begin: number of fields to skip at the beginning of values
    :param skip_end: number of fields to skip at the end of values
    :returns: True if the two lists have the same values, False otherwise
    """
    for idx in range(skip_begin, len(values1) - skip_end):
        try:
            # Use np.isclose() for numbers
            match = np.isclose(values1[idx], values2[idx])
        except TypeError:
            # Use == for strings
            match = values1[idx] == values2[idx]
        if not match:
            return False
    return True


def _event_exists(cursor, values, skip_begin=0, skip_end=0):
    """
    Check if an event exists in the database, based on values.

    :param cursor: database cursor
    :param values: list of values
    :param skip_begin: number of fields to skip at the beginning of values
    :param skip_end: number of fields to skip at the end of values
    :returns: True if event exists, False otherwise
    """
    evid = values[0]
    cursor.execute('SELECT * FROM events WHERE evid = ?', (evid,))
    rows = cursor.fetchall()
    rows_with_same_values = [
        row for row in rows
        if _same_values(values, row, skip_begin, skip_end)
    ]
    return len(rows_with_same_values) > 0


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
    Get a list of database fields, number of standard fields, and number of
    extra fields.

    :param config: config object
    :returns: list of field definitions, number of standard fields,
              number of extra fields
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
    n_standard_fields = len(field_definitions)
    extra_field_names = config['extra_field_names'] or []
    extra_field_types = config['extra_field_types'] or []
    n_extra_fields = len(extra_field_names)
    field_definitions.extend(
        f'{name} {dbtype}' for name, dbtype
        in zip(extra_field_names, extra_field_types))
    return field_definitions, n_standard_fields, n_extra_fields


def _get_db_values_from_event(ev, config):
    """
    Get a list of values from an obspy event object.

    :param ev: obspy event object
    :param config: config object
    :returns: list of values
    :raises ValueError: if event has no origin
    """
    evid = _get_evid(str(ev.resource_id.id))
    version = 1
    try:
        orig = ev.preferred_origin() or ev.origins[0]
    except IndexError as e:
        raise ValueError(f'Event {evid} has no origin') from e
    time = str(orig.time)
    lat = orig.latitude
    lon = orig.longitude
    depth = orig.depth / 1e3  # km
    try:
        magnitude = ev.preferred_magnitude() or ev.magnitudes[0]
        mag = magnitude.mag
        mag_type = magnitude.magnitude_type
    except IndexError:
        mag = None
        mag_type = None
    event_type = ev.event_type
    values = [
        evid, version, time, lat, lon, depth, mag, mag_type, event_type]
    # add extra fields
    extra_field_defaults = config['extra_field_defaults'] or []
    values += extra_field_defaults
    return values


def _add_event_to_db(
        config, ev, cursor, initdb, n_standard_fields, n_extra_fields):
    """
    Add an obspy event to the database.

    :param config: config object
    :param ev: obspy event object
    :param cursor: database cursor
    :param initdb: if True, create new database file
    :param n_standard_fields: number of standard fields
    :param n_extra_fields: number of extra fields

    :returns: number of events created, number of events updated
    """
    values = _get_db_values_from_event(ev, config)
    evid, version = values[:2]
    ncreated = nupdated = 0
    # skip evid and ver fields as well as extra fields
    if _event_exists(cursor, values, skip_begin=2, skip_end=n_extra_fields):
        return ncreated, nupdated
    if initdb or config['overwrite_updated_events']:
        # if the event exists, get the values of extra fields
        ev_exists = False
        cursor.execute(
            'SELECT * FROM events WHERE evid = ? AND ver = ?',
            (evid, version))
        row = cursor.fetchone()
        if row is not None:
            ev_exists = True
            row = list(row)
            # merge event values with existing extra field values
            values = values[:n_standard_fields] + row[n_standard_fields:]
        # add events to table, replace events that already exist
        cursor.execute(
            'INSERT OR REPLACE INTO events VALUES '
            f'({", ".join("?" * len(values))})', values)
        if ev_exists:
            nupdated = cursor.rowcount
        else:
            ncreated = cursor.rowcount
        return ncreated, nupdated
    # add event to table, increment version if evid already exists
    while True:
        ev_exists = False
        try:
            cursor.execute(
                'INSERT INTO events VALUES '
                f'({", ".join("?" * len(values))})', values)
            if ev_exists:
                nupdated = cursor.rowcount
            else:
                ncreated = cursor.rowcount
            break
        except sqlite3.IntegrityError:
            # evid and ver already exist
            ev_exists = True
            # increment version in the values list
            values[1] += 1
    return ncreated, nupdated


def write_catalog_to_db(cat, config, initdb):
    """
    Write catalog to database.

    :param cat: obspy Catalog object
    :param config: config object
    :param initdb: if True, create new database file
    """
    conn = _get_db_connection(config, initdb)
    cursor = conn.cursor()
    if initdb:
        _set_db_version(cursor)
    else:
        _check_db_version(cursor, config)
    field_definitions, n_standard_fields, n_extra_fields =\
        _get_db_field_definitions(config)
    # create table if it doesn't exist, use evid and ver as primary key
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS events '
        f'({", ".join(field_definitions)}, PRIMARY KEY (evid, ver))')
    events_created = 0
    events_updated = 0
    for ev in cat:
        try:
            _ncreated, _nupdated = _add_event_to_db(
                config, ev, cursor, initdb, n_standard_fields, n_extra_fields)
        except ValueError as e:
            print(e)
            continue
        events_created += _ncreated
        events_updated += _nupdated
    # close database connection
    conn.commit()
    if events_created:
        plural = 's' if events_created > 1 else ''
        print(
            f'{events_created} new event{plural} added to the database '
            f'"{config["db_file"]}"'
        )
    if events_updated:
        plural = 's' if events_updated > 1 else ''
        print(
            f'{events_updated} event{plural} updated in the database '
            f'"{config["db_file"]}"'
        )
    if not events_created and not events_updated:
        print('No new events added or updated in the database')


def _process_where_option(where_str):
    """
    Process the `where` option to create a SQL WHERE filter with "?"
    placeholders and a list of values.

    :param where_str: string passed to the `where` option
    :returns: SQL WHERE filter, list of values
    """
    # Define a regular expression pattern to match key-value pairs
    # with optional spaces around operators. Possible operators are
    # =, <, >, <=, >=, !=
    pattern = re.compile(r'(\w+)\s*([><!=]+)\s*([\w\d.]+)')
    # Find all the matches in the `where` string
    matches = pattern.findall(where_str)
    # Extract values
    values = [match[2] for match in matches]
    # Create the where filter by replacing the key-op-value pattern with
    # key-op-? to create a placeholder for the value.
    where_filter = pattern.sub(r'\1\2?', where_str)
    return where_filter, values


def _build_query(
        cursor, config, eventid=None, version=None, field_list=None,
        honor_where_filter=True):
    """
    Build a query to read events from the database.

    :param config: config object
    :param eventid: limit to events with this evid. If ``None``, then the
                    eventid is taken from the command line arguments via
                    ``config['args']``
    :param version: limit to events with this version. If ``None``, then the
                    version is taken from the command line arguments via
                    ``config['args']``
    :param field_list: list of fields to read from the database
    :param honor_where_filter: if ``True``, honor the ``where`` option
    :param cursor: database cursor

    :returns: query, query values, fields

    :note: if a ``field_list`` is provided, a ``time`` field is always added
    to the query, for sorting purposes.
    """
    args = config['args']
    if eventid is None:
        eventid = getattr(args, 'eventid', None)
        if eventid == 'ALL':
            eventid = None
    if eventid is not None:
        # raise ValueError if eventid is not in database
        cursor.execute('SELECT * FROM events WHERE evid = ?', (eventid,))
        if not cursor.fetchall():
            raise ValueError(f'Event {eventid} not found in database')
    if version is None:
        version = getattr(args, 'event_version', None)
    where = getattr(args, 'where', None) if honor_where_filter else None
    if field_list is not None:
        # always query time and version, for sorting
        fields = field_list + ['time', 'ver']
        query = f'SELECT {", ".join(fields)} FROM events'
    else:
        # read field names
        cursor.execute('PRAGMA table_info(events)')
        # we just need the field names, which are in the second column
        fields = [f[1] for f in cursor.fetchall()]
        query = 'SELECT * FROM events'
    query_values = []
    if where is not None:
        where_filter, values = _process_where_option(where)
        query = f'{query} WHERE {where_filter}'
        query_values += values
    if eventid is not None:
        query += ' AND evid = ?' if 'WHERE' in query else ' WHERE evid = ?'
        query_values.append(eventid)
    if version is not None:
        query += ' AND ver = ?' if 'WHERE' in query else ' WHERE ver = ?'
        query_values.append(version)
    return query, query_values, fields


def _keep_latest_version(rows, fields):
    """
    Keep only the latest version of each event in the list of rows.

    :param rows: list of rows
    :param fields: list of fields

    :returns: list of kept rows
    """
    evid_index = fields.index('evid')
    ver_index = fields.index('ver')
    evids = set()
    rows_to_keep = []
    for row in sorted(
        rows, key=lambda r: (r[evid_index], r[ver_index]), reverse=True
    ):
        evid = row[evid_index]
        if evid not in evids:
            rows_to_keep.append(row)
            evids.add(evid)
    return rows_to_keep


def _sort_rows_by_time_and_version(rows, fields, reverse=False):
    """
    Sort rows by time and version; reverse if needed.

    :param rows: list of rows
    :param fields: list of fields
    :param reverse: if True, sort in reverse order

    :returns: sorted fields, sorted rows
    """
    time_index = fields.index('time')
    ver_index = fields.index('ver')
    rows.sort(key=lambda r: (r[time_index], r[ver_index]), reverse=reverse)
    # if last two fields are 'time' and 'ver', they were added for sorting
    # purposes and should be removed
    if fields[-2] == 'time' and fields[-1] == 'ver':
        fields = fields[:-2]
        rows = [r[:-2] for r in rows]
    return fields, rows


def read_fields_and_rows_from_db(
        config, eventid=None, version=None, field_list=None,
        honor_where_filter=True):
    """
    Read fields and rows from database. Return a list of fields and a list of
    rows. The rows are sorted by time and version.

    :param config: config object
    :param eventid: limit to events with this evid. If ``None``, then the
                    eventid is taken from the command line arguments via
                    ``config['args']``
    :param version: limit to events with this version. If ``None``, then the
                    version is taken from the command line arguments via
                    ``config['args']``
    :param field_list: list of fields to read from the database
    :param honor_where_filter: if ``True``, honor the ``where`` option

    :returns: list of fields, list of rows
    :raises ValueError: if field is not found in database
    """
    conn = _get_db_connection(config)
    cursor = conn.cursor()
    query, query_values, fields = _build_query(
        cursor, config, eventid, version, field_list, honor_where_filter)
    try:
        cursor.execute(query, query_values)
    except sqlite3.OperationalError as e:
        field = e.args[0].split()[-1]
        raise ValueError(f'Field "{field}" not found in database') from e
    rows = cursor.fetchall()
    conn.close()
    if not getattr(config['args'], 'allversions', True):
        rows = _keep_latest_version(rows, fields)
    reverse = getattr(config['args'], 'reverse', False)
    return _sort_rows_by_time_and_version(rows, fields, reverse)


def replicate_event_in_db(config, eventid, version=1):
    """
    Replicate an event in the database. The new event will have the same
    evid as the original event, but a different version.

    :param config: config object
    :param eventid: event id of the original event
    :param version: version of the original event

    :raises ValueError: if eventid/version is not found in database
    """
    fields, rows = read_fields_and_rows_from_db(
        config, eventid=eventid, version=version)
    if not rows:
        raise ValueError(
            f'Event {eventid} version {version} not found in database')
    row = list(rows[0])
    # increment version
    ver_index = fields.index('ver')
    row[ver_index] += 1
    conn = _get_db_connection(config)
    c = conn.cursor()
    while True:
        try:
            c.execute(
                'INSERT INTO events VALUES '
                f'({", ".join("?" * len(row))})', row)
            break
        except sqlite3.IntegrityError:
            # version already exists, increment version and try again
            row[ver_index] += 1
    # close database connection
    conn.commit()
    print(f'Added event {eventid} version {row[ver_index]} to database')


def delete_event_from_db(config, eventid, version=None):
    """
    Delete an event from the database.

    :param config: config object
    :param eventid: event id of the event to delete
                    (if None, delete all events for the given version)
    :param version: version of the event to delete
                    (if None, delete all versions of the event)
    """
    msg = None
    conn = _get_db_connection(config)
    c = conn.cursor()
    if eventid is None and version is None:
        c.execute('DELETE FROM events')
        msg = 'All events deleted from database'
    elif eventid is None:
        c.execute('DELETE FROM events WHERE ver = ?', (version,))
        msg = f'All events of version {version} deleted from database'
    if eventid is not None and version is not None:
        c.execute(
            'DELETE FROM events WHERE evid = ? AND ver = ?',
            (eventid, version))
        msg = f'Event {eventid} version {version} deleted from database'
    elif eventid is not None:
        c.execute('DELETE FROM events WHERE evid = ?', (eventid,))
        msg = f'Event {eventid} deleted from database'
    if msg is None:
        # this should never happen
        raise ValueError('Invalid combination of eventid and version')
    # close database connection
    conn.commit()
    print(msg)


def update_event_in_db(config, eventid, version, field, value):
    """
    Update an event in the database.

    :param config: config object
    :param eventid: event id of the event to update
    :param version: version of the event to update
    :param field: field to update
    :param value: new value

    :raises ValueError: if field is not found in database
    """
    conn = _get_db_connection(config)
    c = conn.cursor()
    try:
        c.execute(
            f'UPDATE events SET {field} = ? WHERE evid = ? AND ver = ?',
            (value, eventid, version))
    except sqlite3.OperationalError as e:
        raise ValueError(f'Field "{field}" not found in database') from e
    # close database connection
    conn.commit()
    print(
        f'Updated field "{field}={value}" '
        f'for event {eventid} version {version}')


def increment_event_in_db(config, eventid, version, field, value):
    """
    Increment an event in the database.

    :param config: config object
    :param eventid: event id of the event to update
    :param version: version of the event to update
    :param field: field to update
    :param value: value to increment, must be a number

    :raises ValueError: if field is not found in database,
                        or if value is not a number
    """
    conn = _get_db_connection(config)
    c = conn.cursor()
    # check if value is numeric
    try:
        value = float(value)
    except ValueError as e:
        raise ValueError(f'Value "{value}" is not a number') from e
    # if value is an integer, convert it to int
    if value == int(value):
        value = int(value)
    # read old value from database and check if it is numeric
    try:
        c.execute(
            f'SELECT {field} FROM events WHERE evid = ? AND ver = ?',
            (eventid, version))
        old_value = c.fetchone()[0]
        try:
            new_value = float(old_value) + value
            if new_value == int(new_value):
                new_value = int(new_value)
        except ValueError as e:
            raise ValueError(f'Field "{field}" is not a number') from e
    except sqlite3.OperationalError as e:
        raise ValueError(f'Field "{field}" not found in database') from e
    # update database
    try:
        c.execute(
            f'UPDATE events SET {field} = ? '
            'WHERE evid = ? AND ver = ?',
            (new_value, eventid, version))
    except sqlite3.OperationalError as e:
        raise ValueError(f'Field "{field}" not found in database') from e
    # close database connection
    conn.commit()
    print(
        f'Field "{field}" incremented by "{value}" '
        f'for event {eventid} version {version}')


def read_events_from_db(config, eventid=None, version=None):
    """
    Read events from database. Return a list of events.

    :param config: config object
    :param eventid: limit to events with this evid
    :param version: limit to events with this version

    :returns: list of events, each event is a dictionary-like object
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config, eventid, version)
    events_list = EventList()
    for event in rows:
        event_dict = Event(zip(fields, event))
        events_list.append(event_dict)
    return events_list


def read_evids_and_versions_from_db(config):
    """
    Get a list of event ids and versions from the database.

    This function only onors the ``allversions`` option
    but not the ``where`` option.

    :param config: config object
    :returns: list of tuples (evid, version)
    """
    _fields, rows = read_fields_and_rows_from_db(
        config, field_list=['evid', 'ver'], honor_where_filter=False)
    return rows


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
    stats_str = f'{nevents} events from {tmin} to {tmax}'
    mags = [event['mag'] for event in events if event['mag'] is not None]
    if mags:
        mag_min = min(mags)
        mag_max = max(mags)
        stats_str += f'\nMagnitude range: {mag_min:.1f} -- {mag_max:.1f}'
    return stats_str

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
            'Do you want to overwrite it? [y/N] '
        )
        if ans not in ['y', 'Y']:
            err_exit('Database file already exists. Exiting.')
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
    # table fields: name TYPE
    fields = [
        'evid TEXT PRIMARY KEY',
        'time TEXT',
        'lat REAL',
        'lon REAL',
        'dep REAL',
        'mag REAL',
        'mag_type TEXT',
        'event_type TEXT',
    ]
    extra_field_names = config['extra_field_names'] or []
    extra_field_types = config['extra_field_types'] or []
    fields.extend(
        f'{name} {dbtype}' for name, dbtype
        in zip(extra_field_names, extra_field_types))
    # create table if it doesn't exist
    c.execute(f'CREATE TABLE IF NOT EXISTS events ({", ".join(fields)})')
    events_written = 0
    for ev in cat:
        evid = str(ev.resource_id.id).split('/')[-1]
        orig = ev.preferred_origin() or ev.origins[0]
        time = str(orig.time)
        lat = orig.latitude
        lon = orig.longitude
        dep = orig.depth / 1e3  # km
        magntiude = ev.preferred_magnitude() or ev.magnitudes[0]
        mag = magntiude.mag
        mag_type = magntiude.magnitude_type
        event_type = ev.event_type
        values = [evid, time, lat, lon, dep, mag, mag_type, event_type]
        # add extra fields
        extra_field_defaults = config['extra_field_defaults'] or []
        values += extra_field_defaults
        if initdb:
            # add events to table, replace events that already exist
            c.execute(
                'INSERT OR REPLACE INTO events VALUES '
                f'({", ".join("?" * len(values))})', values)
        else:
            # add events to table, ignore events that already exist
            c.execute(
                'INSERT OR IGNORE INTO events VALUES '
                f'({", ".join("?" * len(values))})', values)
        events_written += c.rowcount
    # close database connection
    conn.commit()
    print(f'Wrote {events_written} events to database "{config["db_file"]}"')

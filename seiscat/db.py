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


def check_db_exists(config):
    """
    Check if database file exists.

    :param config: config object
    """
    if not os.path.exists(config['db_file']):
        return
    ans = input(
        f'"{config["db_file"]}" already exists. '
        'Do you want to overwrite it? [y/N] '
    )
    if ans not in ['y', 'Y']:
        err_exit('Database file already exists. Exiting.')
    else:
        os.rename(
            config['db_file'], f'{config["db_file"]}.bak')
        print(
            f'Backup of "{config["db_file"]}" saved to '
            f'"{config["db_file"]}.bak"')


def write_catalog_to_db(cat, config, replace=False):
    """
    Write catalog to database.

    :param cat: obspy Catalog object
    :param config: config object
    """
    # open database connection
    conn = sqlite3.connect(config['db_file'])
    c = conn.cursor()
    # table fields: name TYPE
    fields = [
        'evid TEXT PRIMARY KEY',
        'time TEXT',
        'lat REAL',
        'lon REAL',
        'dep REAL',
        'mag REAL',
        'mag_type TEXT'
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
        values = [evid, time, lat, lon, dep, mag, mag_type]
        # add extra fields
        extra_field_defaults = config['extra_field_defaults'] or []
        values += extra_field_defaults
        if replace:
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

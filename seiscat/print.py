# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Printing functions for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import json
from .database.dbfunctions import (
    read_fields_and_rows_from_db, get_catalog_stats)
from .utils import err_exit


def _print_catalog_stats(config):
    """
    Print catalog statistics.

    :param config: config object
    """
    print(get_catalog_stats(config))


def _print_catalog_table(config):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # get max length of each field
    max_len = [len(f) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            max_len[i] = max(max_len[i], len(str(val)))
    # print header
    for i, f in enumerate(fields):
        print(f'{f:{max_len[i]}}', end=' ')
    print()
    for row in rows:
        for i, val in enumerate(row):
            val = 'None' if val is None else val
            print(f'{val:{max_len[i]}}', end=' ')
        print()


def _print_catalog_csv(config):
    """
    Print catalog as CSV.

    :param config: config object
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # print header
    print(','.join(fields))
    for row in rows:
        print(','.join([str(val) for val in row]))


def _print_catalog_geojson(config):
    """
    Print catalog as GeoJSON.

    :param config: config object
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # Find indices of coordinate fields
    try:
        lon_idx = fields.index('lon')
        lat_idx = fields.index('lat')
        depth_idx = fields.index('depth') if 'depth' in fields else None
    except ValueError as e:
        raise ValueError(f'Required field not found: {e}') from e
    # Build GeoJSON FeatureCollection
    features = []
    for row in rows:
        # Extract coordinates
        lon = row[lon_idx]
        lat = row[lat_idx]
        # Convert depth from meters to km for GeoJSON (standard)
        depth = row[depth_idx] / 1000.0 if depth_idx is not None else 0
        # Build properties dictionary with all fields except coordinates
        properties = {}
        for i, field in enumerate(fields):
            val = row[i]
            # Convert time to ISO format string if it's the time field
            if field == 'time' and val is not None:
                val = str(val)
            # Handle None values
            if val is None:
                val = None
            properties[field] = val
        # Create GeoJSON feature
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [lon, lat, depth]
            },
            'properties': properties
        }
        features.append(feature)
    # Create FeatureCollection
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    # Print formatted GeoJSON
    print(json.dumps(geojson, indent=2))


def print_catalog(config):
    """
    Print catalog.

    :param config: config object
    """
    args = config['args']
    try:
        if args.format == 'stats':
            _print_catalog_stats(config)
        elif args.format == 'table':
            _print_catalog_table(config)
        elif args.format == 'csv':
            _print_catalog_csv(config)
        elif args.format == 'geojson':
            _print_catalog_geojson(config)
        else:
            err_exit(f'Unknown format "{args.format}"')
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Export functions for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import json
from .database.dbfunctions import read_fields_and_rows_from_db
from .utils import err_exit


def _export_catalog_csv(config):
    """
    Export catalog as CSV.

    :param config: config object
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    outfile = config['args'].outfile
    try:
        with open(outfile, 'w', encoding='utf-8') as fp:
            # print header
            fp.write(','.join(fields) + '\n')
            for row in rows:
                fp.write(','.join([str(val) for val in row]) + '\n')
        print(f'Catalog exported to "{outfile}"')
    except IOError as e:
        err_exit(f'Error writing to file "{outfile}": {e}')


def _export_catalog_geojson(config):
    """
    Export catalog as GeoJSON.

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
    # Write GeoJSON to file
    outfile = config['args'].outfile
    try:
        with open(outfile, 'w', encoding='utf-8') as fp:
            json.dump(geojson, fp, indent=2)
        print(f'Catalog exported to "{outfile}"')
    except IOError as e:
        err_exit(f'Error writing to file "{outfile}": {e}')


def export_catalog(config):
    """
    Export catalog.

    :param config: config object
    """
    args = config['args']
    out_format = args.format
    if out_format is None:
        # Infer format from file extension
        outfile = args.outfile
        if outfile.endswith('.csv'):
            out_format = 'csv'
            print('Inferred output format "csv" from file extension')
        elif outfile.endswith('.geojson') or outfile.endswith('.json'):
            out_format = 'json'
            print('Inferred output format "json" from file extension')
        else:
            err_exit(
                'Cannot infer output format from file extension. '
                'Please specify the format with the -f option.'
            )
    try:
        if out_format == 'csv':
            _export_catalog_csv(config)
        elif out_format == 'json':
            _export_catalog_geojson(config)
        else:
            err_exit(f'Unknown format "{out_format}"')
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

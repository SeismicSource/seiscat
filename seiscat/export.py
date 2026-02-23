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
import xml.etree.ElementTree as ET
from .database.dbfunctions import read_fields_and_rows_from_db
from .utils import err_exit

# KML Balloon Style configuration
# Controls how balloons display in Google Earth
KML_BALLOON_STYLE_TEXT = '$[description]'


def _get_field_indices(fields):
    """
    Get indices of coordinate and optional magnitude fields.

    :param fields: list of field names
    :return: tuple of (lon_idx, lat_idx, depth_idx, mag_idx)
    """
    try:
        lon_idx = fields.index('lon')
        lat_idx = fields.index('lat')
        depth_idx = fields.index('depth') if 'depth' in fields else None
        mag_idx = fields.index('mag') if 'mag' in fields else None
        return lon_idx, lat_idx, depth_idx, mag_idx
    except ValueError as e:
        raise ValueError(f'Required field not found: {e}') from e


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
    lon_idx, lat_idx, depth_idx, _mag_idx = _get_field_indices(fields)
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


def _process_row_kml(
    document, row, fields, lon_idx, lat_idx, depth_idx, mag_idx, scale_factor
):
    """
    Process a single event row and add it as a placemark to the KML document.

    :param document: KML Document element
    :param row: event row data
    :param fields: list of field names
    :param lon_idx: index of longitude field
    :param lat_idx: index of latitude field
    :param depth_idx: index of depth field
    :param mag_idx: index of magnitude field
    :param scale_factor: factor to scale icon size based on magnitude
    """
    placemark = ET.SubElement(document, 'Placemark')
    # Get event ID or use index
    evid = row[fields.index('evid')] if 'evid' in fields else str(row[0])
    name_elem = ET.SubElement(placemark, 'name')
    name_elem.text = str(evid)
    # Build description with event properties
    desc_parts = []
    for i, field in enumerate(fields):
        if field == 'evid':
            continue
        val = row[i]
        if field == 'time' and val is not None:
            val = str(val)
        if val is not None:
            desc_parts.append(f'{field}: {val}')
    description_elem = ET.SubElement(placemark, 'description')
    description_elem.text = (
        f'<b><big>{evid}</big></b><br/><br/>'
        + '<br/>'.join(desc_parts)
    )
    # Set point coordinates and depth
    lon = row[lon_idx]
    lat = row[lat_idx]
    # Convert depth from meters to km for KML (standard)
    depth = row[depth_idx] / 1000.0 if depth_idx is not None else 0
    point = ET.SubElement(placemark, 'Point')
    coordinates = ET.SubElement(point, 'coordinates')
    coordinates.text = f'{lon},{lat},{depth}'
    # Style based on magnitude if available
    style = ET.SubElement(placemark, 'Style')
    # Suppress driving directions in balloon
    balloon_style = ET.SubElement(style, 'BalloonStyle')
    balloon_text = ET.SubElement(balloon_style, 'text')
    balloon_text.text = KML_BALLOON_STYLE_TEXT
    # Hide label text
    label_style = ET.SubElement(style, 'LabelStyle')
    label_scale = ET.SubElement(label_style, 'scale')
    label_scale.text = '0'
    icon_style = ET.SubElement(style, 'IconStyle')
    # Icon scale (adjust for size based on magnitude)
    icon_scale = ET.SubElement(icon_style, 'scale')
    # Use a circular icon
    icon = ET.SubElement(icon_style, 'Icon')
    href = ET.SubElement(icon, 'href')
    href.text = (
        'http://maps.google.com/mapfiles/kml/shapes/'
        'placemark_circle.png'
    )
    # Color and size based on magnitude (ABGR format!)
    color = ET.SubElement(icon_style, 'color')
    mag = row[mag_idx] if mag_idx is not None else None
    try:
        mag_val = float(mag)
        # Log scaling: size grows exponentially with magnitude.
        # scale_factor=5.0 gives icon_scale=1.0 at mag=5.0.
        icon_scale.text = str(
            min(
                5.0,
                max(0.3, scale_factor / 5.0 * 10 ** ((mag_val - 5.0) / 10.0))
            )
        )
        if mag_val < 3.0:
            color.text = 'ff00ff00'   # green
        elif mag_val < 5.0:
            color.text = 'ff00ffff'   # yellow
        elif mag_val < 6.5:
            color.text = 'ff0080ff'   # orange
        else:
            color.text = 'ff0000ff'   # red
    except (TypeError, ValueError):
        icon_scale.text = '0.7'
        color.text = 'ffff0000'       # blue


def _create_kml_document():
    """
    Create a KML document with BalloonStyle configuration.

    The BalloonStyle controls how balloons display in Google Earth.
    Setting text to KML_BALLOON_STYLE_TEXT shows only the description
    element and suppresses driving directions and other default elements.

    :return: tuple of (kml_element, document_element)
    """
    kml = ET.Element('kml', attrib={'xmlns': 'http://www.opengis.net/kml/2.2'})
    document = ET.SubElement(kml, 'Document')
    description = ET.SubElement(document, 'description')
    description.text = 'Exported from seiscat'
    return kml, document


def _export_catalog_kml(config, scale_factor=5.0):
    """
    Export catalog as KML.

    :param config: config object
    :param scale_factor: scale factor for marker size (default: 5.0).
                        Larger values produce larger markers.
    """
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # Find indices of coordinate fields
    lon_idx, lat_idx, depth_idx, mag_idx = _get_field_indices(fields)
    # Create KML root element with document and BalloonStyle
    kml, document = _create_kml_document()
    # Add placemarks for each event
    for row in rows:
        _process_row_kml(
            document, row, fields, lon_idx, lat_idx, depth_idx, mag_idx,
            scale_factor
        )
    # Write KML to file
    outfile = config['args'].outfile
    try:
        tree = ET.ElementTree(kml)
        ET.indent(tree, space='  ')
        with open(outfile, 'w', encoding='utf-8') as fp:
            fp.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(fp, encoding='unicode', xml_declaration=False)
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
            print('Inferred output format "geojson" from file extension')
        elif outfile.endswith('.kml'):
            out_format = 'kml'
            print('Inferred output format "kml" from file extension')
        else:
            err_exit(
                'Cannot infer output format from file extension. '
                'Please specify the format with the -f option.'
            )
    # Add file extension if missing
    if not args.outfile.lower().endswith(f'.{out_format}'):
        args.outfile += f'.{out_format}'
    try:
        if out_format == 'csv':
            _export_catalog_csv(config)
        elif out_format == 'json':
            _export_catalog_geojson(config)
        elif out_format == 'kml':
            _export_catalog_kml(config, scale_factor=args.scale)
        else:
            err_exit(f'Unknown format "{out_format}"')
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

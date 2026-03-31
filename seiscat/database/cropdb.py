# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Crop functions for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from obspy import Catalog
from obspy.geodetics import locations2degrees
from ..utils import ExceptionExit, err_exit
from .dbfunctions import (
    backup_db, check_db_exists, read_fields_and_rows_from_db,
    delete_event_from_db)


def _confirm_cropdb(config):
    """Ask user confirmation before cropping the database.

    The prompt explicitly warns that a backup file will be created before
    events are deleted.

    :param config: config object
    """
    db_file = config['db_file']
    prompt = (
        f'Crop database "{db_file}" to match the selection criteria?\n'
        f'A backup will be created first at "{db_file}.bak". '
        '[y/N] '
    )
    try:
        answer = input(prompt)
    except EOFError:
        err_exit('Aborted')
    if answer.lower() != 'y':
        err_exit('Aborted')


def _criteria_is_defined(config, suffix=''):
    """Check whether a criteria set is defined in the configuration.

    The function inspects all supported keys for the given suffix
    (geographic box, circular selection, depth, magnitude and event-type
    include/exclude filters) and reports whether at least one of them
    contains a non-``None`` value.

    :param config: configuration object used by seiscat.
    :param suffix: suffix appended to criteria keys (for example ``''``,
        ``'_1'``, ``'_2'``).
    :returns: ``True`` if at least one criterion is defined,
        otherwise ``False``.
    """
    keys = [
        f'lat_min{suffix}', f'lat_max{suffix}',
        f'lon_min{suffix}', f'lon_max{suffix}',
        f'lat0{suffix}', f'lon0{suffix}',
        f'radius_min{suffix}', f'radius_max{suffix}',
        f'depth_min{suffix}', f'depth_max{suffix}',
        f'mag_min{suffix}', f'mag_max{suffix}',
        f'event_type{suffix}', f'event_type_exclude{suffix}',
    ]
    return any(config.get(k) is not None for k in keys)


def _is_outside_range(value, lower, upper):
    """Determine whether a numeric value falls outside a closed interval.

    Missing values are treated as unconstrained:
    - if ``value`` is ``None`` the function returns ``False``;
    - if ``lower`` is ``None`` no lower-bound check is applied;
    - if ``upper`` is ``None`` no upper-bound check is applied.

    :param value: value to validate.
    :param lower: inclusive lower bound, or ``None``.
    :param upper: inclusive upper bound, or ``None``.
    :returns: ``True`` when ``value`` is outside the active bounds,
        otherwise ``False``.
    """
    return value is not None and (
        (lower is not None and value < lower)
        or (upper is not None and value > upper)
    )


def _matches_geographic_criteria(lat, lon, config, suffix=''):
    """Evaluate geographic criteria for one event.

    This helper applies either:
    - box selection using ``lat_min/lat_max/lon_min/lon_max``, or
    - circular selection using ``lat0/lon0/radius_min/radius_max``.

    Circular selection takes precedence when both ``lat0`` and ``lon0`` are
    defined, to match the same precedence used by FDSN-based selection.

    :param lat: event latitude in decimal degrees, or ``None``.
    :param lon: event longitude in decimal degrees, or ``None``.
    :param config: configuration object used by seiscat.
    :param suffix: suffix appended to criteria keys.
    :returns: ``True`` if the event satisfies geographic criteria,
        otherwise ``False``.
    """
    lat_min = config.get(f'lat_min{suffix}')
    lat_max = config.get(f'lat_max{suffix}')
    lon_min = config.get(f'lon_min{suffix}')
    lon_max = config.get(f'lon_max{suffix}')
    lat0 = config.get(f'lat0{suffix}')
    lon0 = config.get(f'lon0{suffix}')
    radius_min = config.get(f'radius_min{suffix}')
    radius_max = config.get(f'radius_max{suffix}')

    # Geographic selection: circle takes precedence over box.
    if lat0 is None or lon0 is None:
        return not (
            _is_outside_range(lat, lat_min, lat_max)
            or _is_outside_range(lon, lon_min, lon_max)
        )

    if lat is None or lon is None:
        return True

    dist_deg = locations2degrees(lat0, lon0, lat, lon)
    return not _is_outside_range(dist_deg, radius_min, radius_max)


def _matches_numeric_criteria(depth, mag, config, suffix=''):
    """Evaluate depth and magnitude criteria for one event.

    The function checks event depth against ``depth_min/depth_max`` and
    magnitude against ``mag_min/mag_max`` for the selected suffix.

    :param depth: event depth in km (positive down), or ``None``.
    :param mag: event magnitude, or ``None``.
    :param config: configuration object used by seiscat.
    :param suffix: suffix appended to criteria keys.
    :returns: ``True`` if both depth and magnitude satisfy active criteria,
        otherwise ``False``.
    """
    depth_min = config.get(f'depth_min{suffix}')
    depth_max = config.get(f'depth_max{suffix}')
    mag_min = config.get(f'mag_min{suffix}')
    mag_max = config.get(f'mag_max{suffix}')

    return not (
        _is_outside_range(depth, depth_min, depth_max)
        or _is_outside_range(mag, mag_min, mag_max)
    )


def _matches_event_type_criteria(event_type, config, suffix=''):
    """Evaluate event-type include/exclude criteria for one event.

    Inclusion and exclusion are evaluated as follows:
    - if no include list is set, all types are initially included;
    - if an include list is set, the event type must be present in it;
    - if an exclude list is set and contains the event type, the event is
      rejected regardless of inclusion.

    :param event_type: event type value for the event, or ``None``.
    :param config: configuration object used by seiscat.
    :param suffix: suffix appended to criteria keys.
    :returns: ``True`` if the event passes event-type filters,
        otherwise ``False``.
    """
    event_types = config.get(f'event_type{suffix}')
    event_types_exclude = config.get(f'event_type_exclude{suffix}')

    included = event_types is None or event_type in event_types
    excluded = (
        event_types_exclude is not None
        and event_type in event_types_exclude
    )
    return included and not excluded


def _event_matches_criteria(
        lat, lon, depth, mag, event_type, config, suffix=''):
    """
    Check if an event matches the selection criteria identified by suffix.

    The geographic circular selection (lat0/lon0/radius) takes precedence
    over the box selection (lat_min/lat_max/lon_min/lon_max) when both are
    defined, consistent with FDSN query behaviour.

    :param lat: event latitude (decimal degrees)
    :param lon: event longitude (decimal degrees)
    :param depth: event depth (km, positive down)
    :param mag: event magnitude
    :param event_type: event type string
    :param config: config object
    :param suffix: suffix appended to config keys (e.g. '' or '_1')
    :returns: ``True`` if the event matches all active criteria in this set,
        ``False`` if at least one criterion fails,
        ``None`` if the criteria set is not defined.
    """
    if not _criteria_is_defined(config, suffix):
        return None

    return (
        _matches_geographic_criteria(lat, lon, config, suffix=suffix)
        and _matches_numeric_criteria(depth, mag, config, suffix=suffix)
        and _matches_event_type_criteria(event_type, config, suffix=suffix)
    )


def _event_matches_config(lat, lon, depth, mag, event_type, config):
    """
    Check if an event matches any of the criteria sets defined in config.

    Events matching at least one criteria set are retained (OR logic across
    criteria sets; AND logic within a single criteria set).

    :param lat: event latitude (decimal degrees)
    :param lon: event longitude (decimal degrees)
    :param depth: event depth (km, positive down)
    :param mag: event magnitude
    :param event_type: event type string
    :param config: config object
    Criteria sets are discovered in sequence as ``''``, ``'_1'``, ``'_2'``,
    and so on, stopping at the first missing suffix.

    :returns: ``True`` if the event matches at least one criteria set,
        or if no criteria are defined at all; otherwise ``False``.
    """
    # Collect all defined criteria sets
    suffixes = ['']
    n = 1
    while _criteria_is_defined(config, suffix=f'_{n}'):
        suffixes.append(f'_{n}')
        n += 1

    if not any(_criteria_is_defined(config, suffix=s) for s in suffixes):
        # No geographic/depth/magnitude criteria defined: keep everything
        return True

    for suffix in suffixes:
        result = _event_matches_criteria(
            lat, lon, depth, mag, event_type, config, suffix=suffix)
        if result is True:
            return True

    return False


def filter_catalog_by_config(cat, config):
    """
    Filter an ObsPy Catalog according to the selection criteria in config.

    Only geographic (box or circle), depth, magnitude and event type
    criteria are evaluated; time-range criteria are ignored because the
    caller is responsible for time filtering when reading from file.

    :param cat: obspy Catalog object
    :param config: config object
    :returns: filtered obspy Catalog object
    """
    # Check if any criterion is defined at all
    suffixes = ['']
    n = 1
    while _criteria_is_defined(config, suffix=f'_{n}'):
        suffixes.append(f'_{n}')
        n += 1
    if not any(_criteria_is_defined(config, suffix=s) for s in suffixes):
        print(
            'Warning: no geographic, depth or magnitude selection criteria '
            'are defined in the configuration file. '
            'The catalog will not be filtered.'
        )
        return cat

    kept = []
    for ev in cat:
        try:
            orig = ev.preferred_origin() or ev.origins[0]
        except IndexError:
            kept.append(ev)
            continue
        lat = orig.latitude
        lon = orig.longitude
        try:
            depth = orig.depth / 1e3
        except TypeError:
            depth = None
        try:
            mag = (ev.preferred_magnitude() or ev.magnitudes[0]).mag
        except IndexError:
            mag = None
        event_type = ev.event_type
        if _event_matches_config(lat, lon, depth, mag, event_type, config):
            kept.append(ev)

    if n_removed := len(cat) - len(kept):
        plural = 's' if n_removed > 1 else ''
        print(
            f'{n_removed} event{plural} removed by bounding-box crop.')
    else:
        print('No events removed by bounding-box crop.')
    return Catalog(events=kept)


def cropdb(config):
    """
    Crop the existing database to the selection criteria defined in config.

    A backup of the database is created before any changes are made.
    Events that do not match any of the geographic, depth, magnitude and
    event-type criteria defined in the configuration are deleted.

    :param config: config object
    """
    # Ensure DB exists
    with ExceptionExit():
        check_db_exists(config, initdb=False)

    # Check that at least one spatial/magnitude criterion is defined
    suffixes = ['']
    n = 1
    while _criteria_is_defined(config, suffix=f'_{n}'):
        suffixes.append(f'_{n}')
        n += 1
    if not any(_criteria_is_defined(config, suffix=s) for s in suffixes):
        err_exit(
            'No geographic, depth or magnitude selection criteria are '
            'defined in the configuration file. Nothing to crop.'
        )

    _confirm_cropdb(config)

    # Backup the database before making any changes
    with ExceptionExit():
        backup_db(config)

    # Read all events (all versions, no where filter)
    with ExceptionExit():
        fields, rows = read_fields_and_rows_from_db(
            config,
            field_list=[
                'evid', 'ver', 'lat', 'lon', 'depth', 'mag', 'event_type'
            ],
            honor_where_filter=False,
            honor_sortby=False,
            honor_reverse=False,
        )

    if not rows:
        print('Database is empty. Nothing to crop.')
        return

    evid_idx = fields.index('evid')
    ver_idx = fields.index('ver')
    lat_idx = fields.index('lat')
    lon_idx = fields.index('lon')
    depth_idx = fields.index('depth')
    mag_idx = fields.index('mag')
    etype_idx = fields.index('event_type')

    n_deleted = 0
    for row in rows:
        evid = row[evid_idx]
        ver = row[ver_idx]
        lat = row[lat_idx]
        lon = row[lon_idx]
        depth = row[depth_idx]
        mag = row[mag_idx]
        event_type = row[etype_idx]
        if not _event_matches_config(
                lat, lon, depth, mag, event_type, config):
            with ExceptionExit():
                delete_event_from_db(config, evid, ver)
            n_deleted += 1

    if n_deleted:
        plural = 's' if n_deleted > 1 else ''
        print(
            f'{n_deleted} event{plural} deleted from the database '
            f'"{config["db_file"]}"'
        )
    else:
        print('No events were outside the defined selection criteria.')

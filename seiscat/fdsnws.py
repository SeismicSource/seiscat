# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
FDNS webservices functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from datetime import timedelta
from obspy import UTCDateTime
from obspy import Catalog
from obspy.clients.fdsn import Client
from .utils import err_exit


def open_fdsn_connection(config):
    """
    Open FDSN connection. Return a FDSN client object.

    :param config: config object
    :returns: FDSN client object
    """
    return Client(config['fdsn_event_url'])


def _to_utc_datetime(time):
    """
    Convert time to UTCDateTime object.

    :param time: time in string format
    :returns: UTCDateTime object or None
    """
    return None if time is None else UTCDateTime(time)


def _parse_time_interval(time_interval):
    """
    Parse time interval string.

    :param time_interval: time interval in string format
    :returns: timedelta object or None
    """
    if time_interval is None:
        return None
    parts = time_interval.split()
    value = int(parts[0])
    unit = parts[1]
    if unit.endswith('s'):
        unit = unit[:-1]
    if unit == 'day':
        return timedelta(days=value)
    elif unit == 'hour':
        return timedelta(hours=value)
    elif unit == 'minute':
        return timedelta(minutes=value)
    elif unit == 'second':
        return timedelta(seconds=value)
    else:
        raise ValueError(f'Invalid time unit: {unit}')


def _query_box_or_circle(client, config, suffix=None, first_query=True):
    """
    Query events from FDSN client based on box or circle criteria in config.

    :param client: FDSN client object
    :param config: config object
    :param suffix: suffix to be added to the config keys
    :param first_query: True if this is the first query
    :returns: obspy Catalog object
    """
    query_keys = [
        'start_time', 'end_time', 'recheck_period',
        'lat_min', 'lat_max', 'lon_min', 'lon_max',
        'lat0', 'lon0', 'radius_min', 'radius_max',
        'depth_min', 'depth_max',
        'mag_min', 'mag_max',
        'event_type', 'event_type_exclude'
    ]
    suffix = '' if suffix is None else suffix
    if suffix:
        query_keys = [k + suffix for k in query_keys]
        try:
            if all(config[k] is None for k in query_keys):
                return Catalog()
        except KeyError:
            return Catalog()
    if all(config[k] is None for k in query_keys):
        err_exit('All query parameters are None. Please set at least one.')
    start_time = _to_utc_datetime(config[f'start_time{suffix}'])
    end_time = _to_utc_datetime(config[f'end_time{suffix}'])
    recheck_period = _parse_time_interval(config[f'recheck_period{suffix}'])
    if not first_query and end_time is None and recheck_period:
        start_time = max(start_time, UTCDateTime() - recheck_period)
    minlatitude = config[f'lat_min{suffix}']
    maxlatitude = config[f'lat_max{suffix}']
    minlongitude = config[f'lon_min{suffix}']
    maxlongitude = config[f'lon_max{suffix}']
    latitude = config[f'lat0{suffix}']
    longitude = config[f'lon0{suffix}']
    minradius = config[f'radius_min{suffix}']
    maxradius = config[f'radius_max{suffix}']
    mindepth = config[f'depth_min{suffix}']
    maxdepth = config[f'depth_max{suffix}']
    minmagnitude = config[f'mag_min{suffix}']
    maxmagnitude = config[f'mag_max{suffix}']
    cat = client.get_events(
        starttime=start_time, endtime=end_time,
        minlatitude=minlatitude, maxlatitude=maxlatitude,
        minlongitude=minlongitude, maxlongitude=maxlongitude,
        latitude=latitude, longitude=longitude,
        minradius=minradius, maxradius=maxradius,
        mindepth=mindepth, maxdepth=maxdepth,
        minmagnitude=minmagnitude, maxmagnitude=maxmagnitude,
    )
    # filter in included event types
    event_type = config[f'event_type{suffix}']
    if event_type:
        cat = Catalog([
            ev for ev in cat
            if ev.event_type in event_type
        ])
    # filter out excluded event types
    event_type_exclude = config[f'event_type_exclude{suffix}']
    if event_type_exclude:
        cat = Catalog([
            ev for ev in cat
            if ev.event_type not in event_type_exclude
        ])
    return cat


def query_events(client, config, first_query=True):
    """
    Query events from FDSN client based on criteria in config.

    :param client: FDSN client object
    :param config: config object
    :param first_query: True if this is the first query
    :returns: obspy Catalog object
    """
    print('Querying events from FDSN server...')
    cat = _query_box_or_circle(client, config, first_query=first_query)
    # see if there are additional queries to be done
    n = 1
    while True:
        _cat = _query_box_or_circle(
            client, config, suffix=f'_{n}', first_query=first_query)
        if not _cat:
            break
        cat += _cat
        n += 1
    print(f'Found {len(cat)} events.')
    return cat

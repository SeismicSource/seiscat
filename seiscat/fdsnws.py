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


def select_events(client, config, first_query=True):
    """
    Select events from FDSN client based on criteria in config.

    :param client: FDSN client object
    :param config: config object
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
    if all(config[k] is None for k in query_keys):
        err_exit('All query parameters are None. Please set at least one.')
    start_time = _to_utc_datetime(config['start_time'])
    end_time = _to_utc_datetime(config['end_time'])
    recheck_period = _parse_time_interval(config['recheck_period'])
    if not first_query and end_time is None and recheck_period:
        start_time = max(start_time, UTCDateTime() - recheck_period)
    cat = client.get_events(
        starttime=start_time, endtime=end_time,
        minlatitude=config['lat_min'], maxlatitude=config['lat_max'],
        minlongitude=config['lon_min'], maxlongitude=config['lon_max'],
        latitude=config['lat0'], longitude=config['lon0'],
        minradius=config['radius_min'], maxradius=config['radius_max'],
        mindepth=config['depth_min'], maxdepth=config['depth_max'],
        minmagnitude=config['mag_min'], maxmagnitude=config['mag_max'],
    )
    # filter in included event types
    if config['event_type']:
        cat = Catalog([
            ev for ev in cat
            if ev.event_type in config['event_type']])
    # filter out excluded event types
    if config['event_type_exclude']:
        cat = Catalog([
            ev for ev in cat
            if ev.event_type not in config['event_type_exclude']])
    # see if there are additional queries to be done
    n = 1
    while True:
        _query_keys = [f'{k}_{n}' for k in query_keys]
        if all(k not in config for k in _query_keys):
            break
        # TODO: do the actual query
    return cat

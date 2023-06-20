# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
FDSN webservices functions for seiscat.

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
from obspy.clients.fdsn.header import FDSNNoDataException
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


class InvalidQuery(Exception):
    """Invalid query exception."""
    pass


class QueryArgs(object):
    """Build query arguments for FDSN client."""
    def __init__(self, config, suffix, first_query):
        """
        Initialize query arguments.

        :param config: config object
        :param suffix: suffix to be added to the config keys
        :param first_query: True if this is the first query
        """
        query_keys = [
            'start_time', 'end_time', 'recheck_period',
            'lat_min', 'lat_max', 'lon_min', 'lon_max',
            'lat0', 'lon0', 'radius_min', 'radius_max',
            'depth_min', 'depth_max',
            'mag_min', 'mag_max',
            'event_type', 'event_type_exclude'
        ]
        if suffix:
            query_keys = [k + suffix for k in query_keys]
        try:
            if all(config[k] is None for k in query_keys):
                raise InvalidQuery(
                    'All query parameters are None. Please set at least one.')
        except KeyError as e:
            raise InvalidQuery('Not all query parameters are set.') from e
        self.starttime = _to_utc_datetime(config[f'start_time{suffix}'])
        self.endtime = _to_utc_datetime(config[f'end_time{suffix}'])
        recheck_period = _parse_time_interval(
            config[f'recheck_period{suffix}'])
        if not first_query and self.endtime is None and recheck_period:
            self.starttime = max(
                self.starttime, UTCDateTime() - recheck_period)
        self.minlatitude = config[f'lat_min{suffix}']
        self.maxlatitude = config[f'lat_max{suffix}']
        self.minlongitude = config[f'lon_min{suffix}']
        self.maxlongitude = config[f'lon_max{suffix}']
        self.latitude = config[f'lat0{suffix}']
        self.longitude = config[f'lon0{suffix}']
        self.minradius = config[f'radius_min{suffix}']
        self.maxradius = config[f'radius_max{suffix}']
        self.mindepth = config[f'depth_min{suffix}']
        self.maxdepth = config[f'depth_max{suffix}']
        self.minmagnitude = config[f'mag_min{suffix}']
        self.maxmagnitude = config[f'mag_max{suffix}']

    def get_query(self):
        """
        Return query arguments as a dictionary.

        :returns: dictionary of query arguments
        """
        return {
            'starttime': self.starttime, 'endtime': self.endtime,
            'minlatitude': self.minlatitude, 'maxlatitude': self.maxlatitude,
            'minlongitude': self.minlongitude,
            'maxlongitude': self.maxlongitude,
            'latitude': self.latitude, 'longitude': self.longitude,
            'minradius': self.minradius, 'maxradius': self.maxradius,
            'mindepth': self.mindepth, 'maxdepth': self.maxdepth,
            'minmagnitude': self.minmagnitude,
            'maxmagnitude': self.maxmagnitude,
        }


def _query_box_or_circle(client, config, suffix=None, first_query=True):
    """
    Query events from FDSN client based on box or circle criteria in config.

    :param client: FDSN client object
    :param config: config object
    :param suffix: suffix to be added to the config keys
    :param first_query: True if this is the first query
    :returns: obspy Catalog object
    """
    suffix = '' if suffix is None else suffix
    query_args = QueryArgs(config, suffix, first_query)
    kwargs = query_args.get_query()
    try:
        cat = client.get_events(**kwargs)
    except FDSNNoDataException:
        cat = Catalog()
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
    try:
        cat = _query_box_or_circle(client, config, first_query=first_query)
    except Exception as e:
        err_exit(e)
    # see if there are additional queries to be done
    n = 1
    while True:
        try:
            _cat = _query_box_or_circle(
                client, config, suffix=f'_{n}', first_query=first_query)
        except InvalidQuery:
            break
        except Exception as e:
            err_exit(e)
        cat += _cat
        n += 1
    print(f'Found {len(cat)} events.')
    return cat

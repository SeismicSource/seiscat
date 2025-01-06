# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
FDSN webservices functions for seiscat.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from datetime import timedelta
from obspy import UTCDateTime
from obspy import Catalog
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNNoDataException


def open_fdsn_connection(config):
    """
    Open FDSN connection. Return a FDSN client object.

    :param config: config object
    :returns: FDSN client object
    """
    fdsn_event_url = config.get('fdsn_event_url')
    if fdsn_event_url is None:
        raise ValueError('FDSN event URL not set.')
    return Client(fdsn_event_url)


def _to_utc_datetime(time):
    """
    Convert time to UTCDateTime object.

    :param time: time in string format
    :returns: UTCDateTime object or None
    """
    if time is None:
        return None
    if time.strip() == '':
        raise ValueError('Empty time string.')
    try:
        return UTCDateTime(time)
    except TypeError:
        try:
            time_interval = _parse_time_interval(time)
            return UTCDateTime() + time_interval
        except ValueError as e:
            raise ValueError(
                f'Invalid time format: {time}.\n'
                'Please use YYYY-MM-DDTHH:MM:SS or '
                'a time interval (typically in the past),\n'
                'e.g., -1 day, -2 hours, -5 minutes, -10 seconds.'
            ) from e


def _parse_time_interval(time_interval):
    """
    Parse time interval string.

    :param time_interval: time interval in string format
    :returns: timedelta object or None
    """
    if time_interval is None:
        return None
    parts = time_interval.split()
    if len(parts) != 2:
        raise ValueError(f'Invalid time interval: {time_interval}.')
    value = int(parts[0])
    unit = parts[1]
    if unit.endswith('s'):
        # remvove plural form
        unit = unit[:-1]
    if unit == 'day':
        return timedelta(days=value)
    if unit == 'hour':
        return timedelta(hours=value)
    if unit == 'minute':
        return timedelta(minutes=value)
    if unit == 'second':
        return timedelta(seconds=value)
    raise ValueError(f'Invalid time unit: {unit}')


class InvalidQuery(Exception):
    """Invalid query exception."""


class QueryArgs():
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
    print(f'Querying events from FDSN server "{config["fdsn_event_url"]}"...')
    cat = _query_box_or_circle(client, config, first_query=first_query)
    # see if there are additional queries to be done
    n = 1
    while True:
        try:
            _cat = _query_box_or_circle(
                client, config, suffix=f'_{n}', first_query=first_query)
        except InvalidQuery:
            break
        cat += _cat
        n += 1
    print(f'Found {len(cat)} events.')
    return cat

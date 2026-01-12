# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Utility functions for the map modules.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np


def get_map_extent_from_events(events):
    """
    Get the map extent from the events.

    :param events: list of events
    :type events: list

    :returns: lon_min, lon_max, lat_min, lat_max
    :rtype: tuple of float
    """
    lon_min = min(event['lon'] for event in events)
    lon_max = max(event['lon'] for event in events)
    lat_min = min(event['lat'] for event in events)
    lat_max = max(event['lat'] for event in events)
    # add some padding
    x_extent = lon_max - lon_min
    lon_min -= 0.1 * x_extent
    lon_max += 0.1 * x_extent
    y_extent = lat_max - lat_min
    lat_min -= 0.1 * y_extent
    lat_max += 0.1 * y_extent
    return lon_min, lon_max, lat_min, lat_max


def _get_map_extent_for_suffix(config, suffix=None):
    """
    Get the map extent for a suffix.

    :param config: config object
    :type config: dict
    :param suffix: suffix to be added to the config keys
    :type suffix: str

    :returns: lon_min, lon_max, lat_min, lat_max
    :rtype: tuple of float or None
    """
    suffix = '' if suffix is None else suffix
    lat_min = config.get(f'lat_min{suffix}', None)
    lat_max = config.get(f'lat_max{suffix}', None)
    lon_min = config.get(f'lon_min{suffix}', None)
    lon_max = config.get(f'lon_max{suffix}', None)
    lat0 = config.get(f'lat0{suffix}', None)
    lon0 = config.get(f'lon0{suffix}', None)
    radius_max = config.get(f'radius_max{suffix}', None)
    if None not in (lat0, lon0, radius_max):
        lat_min = lat0 - radius_max * np.sqrt(2)
        lat_max = lat0 + radius_max * np.sqrt(2)
        lon_min = lon0 - radius_max * np.sqrt(2)
        lon_max = lon0 + radius_max * np.sqrt(2)
        return lon_min, lon_max, lat_min, lat_max
    if None not in (lat_min, lat_max, lon_min, lon_max):
        return lon_min, lon_max, lat_min, lat_max
    return None


def get_map_extent(events, config):
    """
    Get the map extent from the config file.

    :param events: list of events
    :type events: list
    :param config: config object
    :type config: dict

    :returns: lon_min, lon_max, lat_min, lat_max
    :rtype: tuple of float
    """
    ret = _get_map_extent_for_suffix(config)
    if ret is None:
        lon_min = np.nan
        lon_max = np.nan
        lat_min = np.nan
        lat_max = np.nan
    else:
        lon_min, lon_max, lat_min, lat_max = ret
    # see if there are additional limits in the config file
    n = 1
    while True:
        ret = _get_map_extent_for_suffix(config, suffix=f'_{n}')
        if ret is None:
            break
        lon_min_, lon_max_, lat_min_, lat_max_ = ret
        lon_min = np.nanmin((lon_min, lon_min_))
        lon_max = np.nanmax((lon_max, lon_max_))
        lat_min = np.nanmin((lat_min, lat_min_))
        lat_max = np.nanmax((lat_max, lat_max_))
        n += 1
    if np.nan in (lon_min, lon_max, lat_min, lat_max):
        print('No map extent found in the config file. It will be set '
              'automatically based on the events.')
        lon_min, lon_max, lat_min, lat_max = get_map_extent_from_events(
            events)
    return lon_min, lon_max, lat_min, lat_max

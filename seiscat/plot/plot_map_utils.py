# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Utility functions for the map modules.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np


def _get_map_extent_for_suffix(config, suffix=None):
    """
    Get the map extent for a suffix.

    :param config: config object
    :param suffix: suffix to be added to the config keys
    :returns: lon_min, lon_max, lat_min, lat_max
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


def get_map_extent(config):
    """
    Get the map extent from the config file.

    :param config: config object
    :returns: lon_min, lon_max, lat_min, lat_max
    """
    ret = _get_map_extent_for_suffix(config)
    if ret is None:
        lon_min = -179
        lon_max = 180
        lat_min = -75
        lat_max = 80
    else:
        lon_min, lon_max, lat_min, lat_max = ret
    # see if there are additional limits in the config file
    n = 1
    while True:
        ret = _get_map_extent_for_suffix(config, suffix=f'_{n}')
        if ret is None:
            break
        lon_min_, lon_max_, lat_min_, lat_max_ = ret
        lon_min = min(lon_min, lon_min_)
        lon_max = max(lon_max, lon_max_)
        lat_min = min(lat_min, lat_min_)
        lat_max = max(lat_max, lat_max_)
        n += 1
    return lon_min, lon_max, lat_min, lat_max

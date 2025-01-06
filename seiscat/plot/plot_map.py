# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from ..utils import err_exit
from ..database.dbfunctions import read_events_from_db


def plot_catalog_map(config):
    """
    Plot the catalog map.

    :param config: config object
    """
    args = config['args']
    try:
        events = read_events_from_db(config)
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)
    # pylint: disable=import-outside-toplevel
    if args.maptype == 'folium':
        from .plot_map_folium import plot_catalog_map_with_folium
        plot_catalog_map_with_folium(events, config)
        return
    if args.maptype == 'cartopy':
        from .plot_map_cartopy import plot_catalog_map_with_cartopy
        plot_catalog_map_with_cartopy(events, config)
        return
    err_exit(f'Invalid map type "{args.maptype}"')

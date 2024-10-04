# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .utils import err_exit


def plot_catalog_map(config):
    """
    Plot the catalog map.

    :param config: config object
    """
    args = config['args']
    # pylint: disable=import-outside-toplevel
    if args.maptype == 'folium':
        from .plot_map_folium import plot_catalog_map_with_folium
        plot_catalog_map_with_folium(config)
        return
    if args.maptype == 'cartopy':
        from .plot_map_cartopy import plot_catalog_map_with_cartopy
        plot_catalog_map_with_cartopy(config)
        return
    err_exit(f'Invalid map type "{args.maptype}"')

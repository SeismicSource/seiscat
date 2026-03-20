# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from ..utils import err_exit
from ..database.dbfunctions import read_events_from_db
from .plot_utils import get_matplotlib_colormap


def plot_catalog_map(config):
    """
    Plot the catalog map.

    :param config: config object
    """
    args = config['args']
    if getattr(args, 'colorby', None) is not None:
        # Validate the colormap before loading events or importing a backend
        # so invalid names fail immediately at command entry.
        get_matplotlib_colormap(getattr(args, 'colormap', None))
    try:
        events = read_events_from_db(config)
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)
    # pylint: disable=import-outside-toplevel
    if args.backend == 'folium':
        from .plot_map_folium import plot_catalog_map_with_folium
        plot_catalog_map_with_folium(events, config)
        return
    if args.backend == 'cartopy':
        from .plot_map_cartopy import plot_catalog_map_with_cartopy
        plot_catalog_map_with_cartopy(events, config)
        return
    if args.backend == 'plotly':
        from .plot_map_plotly import plot_catalog_map_with_plotly
        plot_catalog_map_with_plotly(events, config)
        return
    err_exit(f'Invalid map backend "{args.backend}"')

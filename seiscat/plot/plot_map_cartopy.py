# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map using cartopy.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np
import matplotlib.pyplot as plt
from .plot_map_utils import get_map_extent
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit
try:
    import cartopy.crs as ccrs
    from cartopy.feature import AdaptiveScaler
except ImportError:
    err_exit(
        'Cartopy is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://scitools.org.uk/cartopy/docs/latest/installing.html'
    )


def _get_tile_scale(extent):
    """
    Get the tile scale for a given extent.

    :param extent: tuple (lon_min, lon_max, lat_min, lat_max)
    :returns: tile scale
    """
    tile_autoscaler = AdaptiveScaler(
        default_scale=4,
        limits=(
            (4, 180), (5, 90), (6, 45), (7, 25), (8, 15), (9, 5),
            (10, 2), (11, 1),
        )
    )
    tile_scale = tile_autoscaler.scale_from_extent(extent)
    # print(f'tile_scale: {tile_scale}')
    return int(tile_scale)


def _plot_events(ax, events, scale):
    """
    Plot events on a map.

    :param events: list of events, each event is a dictionary
    :param scale: scale for event markers
    :param ax: matplotlib axes object
    """
    mags = [e['mag'] for e in events if e['mag'] is not None]
    # use fixed radius if no magnitudes are available
    fixed_radius = not mags
    marker_scale = scale / 10. * 2
    if not fixed_radius:
        # remove events with no magnitude
        events = [e for e in events if e['mag'] is not None]
        radii = [np.exp(e['mag']) * marker_scale for e in events]
    else:
        radii = [3*marker_scale] * len(events)
    ev_attributes = [
        (e['evid'], e['ver'], e['time'], e['lon'], e['lat'], e['depth'],
         e['mag'], radii[n])
        for n, e in enumerate(events)
    ]
    # Sort events by time, so that the latest event is plotted on top
    ev_attributes.sort(key=lambda x: x[2])
    # Collect all coordinates and sizes for batch plotting
    lons = [attr[3] for attr in ev_attributes]
    lats = [attr[4] for attr in ev_attributes]
    sizes = [attr[7] for attr in ev_attributes]
    # Plot all events at once
    ax.scatter(
        lons, lats,
        s=sizes,
        facecolor='red', edgecolor='black',
        zorder=10,
        transform=ccrs.PlateCarree(),
    )


def plot_catalog_map_with_cartopy(events, config):
    """
    Plot the catalog map using cartopy.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj
    """
    out_file = config['args'].out_file
    if out_file:
        valid_exts = (
            '.png', '.pdf', '.svg', '.jpg', '.jpeg', '.tif', '.tiff', '.eps')
        if not out_file.lower().endswith(valid_exts):
            err_exit(
                'Output file for cartopy maps should have one of the '
                f'following extensions:\n  {", ".join(valid_exts)}'
            )
        print(f'Saving map to {out_file}...')
    else:
        print('Building map...')
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Mercator())
    ax.stock_img()
    extent = get_map_extent(events, config)
    ax.set_extent(extent)
    ax.coastlines(resolution='10m', edgecolor='black', linewidth=1)
    ax.add_feature(
        ccrs.cartopy.feature.BORDERS, edgecolor='black', linewidth=1)
    g_kwargs = dict(draw_labels=True, dms=True, x_inline=False, y_inline=False)
    ax.gridlines(**g_kwargs)

    def redraw_gridlines(ax):
        ax.gridlines(**g_kwargs)
    ax.callbacks.connect('xlim_changed', redraw_gridlines)
    scale = config['args'].scale
    _plot_events(ax, events, scale)
    ax.set_title(get_catalog_stats(config))
    if out_file:
        plt.savefig(out_file, bbox_inches='tight')
        print(f'Map saved to {out_file}')
    else:
        plt.show()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map using cartopy.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np
import matplotlib.pyplot as plt
from .db import read_events_from_db, get_catalog_stats
from .utils import err_exit
from .plot_map_utils import get_map_extent
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


def _plot_events(ax, events, scale, plot_version_number=False):
    """
    Plot events on a map.

    :param events: list of events, each event is a dictionary
    :param scale: scale for event markers
    :param ax: matplotlib axes object
    """
    marker_scale = scale / 10. * 2
    # remove events with no magnitude
    events = [e for e in events if e['mag'] is not None]
    ev_attributes = [
        (e['evid'], e['ver'], e['time'], e['lon'], e['lat'], e['depth'],
         e['mag'], np.exp(e['mag']) * marker_scale)
        for e in events
    ]
    # Sort events by time, so that the latest event is plotted on top
    ev_attributes.sort(key=lambda x: x[2])
    markers = []
    for evid, ver, time, lon, lat, depth, mag, size in ev_attributes:
        _evid = f'{evid} v{ver}' if plot_version_number else evid
        marker_label = (
            f'{_evid} M{mag:.1f} {depth:.1f} km\n'
            f'{time.strftime("%Y-%m-%d %H:%M:%S")}')
        marker = ax.scatter(
            lon, lat,
            s=size,
            facecolor='red', edgecolor='black',
            label=marker_label,
            zorder=10,
            transform=ccrs.PlateCarree(),
        )
        markers.append(marker)
    # Empty annotation that will be updated interactively
    annot = ax.annotate(
        '', xy=(0, 0), xytext=(5, 5),
        textcoords='offset points',
        bbox=dict(boxstyle='round', fc='w'),
        zorder=20
    )
    annot.set_visible(False)
    fig = ax.get_figure()

    def hover(event):
        vis = annot.get_visible()
        if vis:
            annot.set_visible(False)
            fig.canvas.draw_idle()
        if event.inaxes != ax:
            return
        for marker in markers:
            cont, _ = marker.contains(event)
            if cont:
                marker.set_linewidth(3)
                annot.xy = (event.xdata, event.ydata)
                annot.set_text(marker.get_label())
                annot.get_bbox_patch().set_facecolor('white')
                annot.get_bbox_patch().set_alpha(0.8)
                annot.set_visible(True)
            else:
                marker.set_linewidth(1)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect('motion_notify_event', hover)


def plot_catalog_map_with_cartopy(config):
    """
    Plot the catalog map using cartopy.

    :param config: config object
    """
    # lazy import cartopy, since it's not an install requirement
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Mercator())
    ax.stock_img()
    extent = get_map_extent(config)
    ax.set_extent(extent)
    ax.coastlines(resolution='10m', edgecolor='black', linewidth=1)
    ax.add_feature(
        ccrs.cartopy.feature.BORDERS, edgecolor='black', linewidth=1)
    g_kwargs = dict(draw_labels=True, dms=True, x_inline=False, y_inline=False)
    ax.gridlines(**g_kwargs)

    def redraw_gridlines(ax):
        ax.gridlines(**g_kwargs)
    ax.callbacks.connect('xlim_changed', redraw_gridlines)
    try:
        events = read_events_from_db(config)
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)
    scale = config['args'].scale
    plot_version_number = config['args'].allversions
    _plot_events(ax, events, scale, plot_version_number)
    ax.set_title(get_catalog_stats(config))
    plt.show()

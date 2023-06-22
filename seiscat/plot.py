# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plotting functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np
import matplotlib.pyplot as plt
from .db import read_events_from_db, get_catalog_stats
from .utils import err_exit


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


def _get_map_extent(config):
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


def _get_tile_scale(extent):
    """
    Get the tile scale for a given extent.

    :param extent: tuple (lon_min, lon_max, lat_min, lat_max)
    :returns: tile scale
    """
    from cartopy.feature import AdaptiveScaler
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
    import cartopy.crs as ccrs
    marker_scale = scale / 10. * 2
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


def plot_catalog_map(config):
    """
    Plot the catalog map.

    :param config: config object
    """
    # lazy import cartopy, since it's not an install requirement
    try:
        import cartopy.crs as ccrs
        import cartopy.io.img_tiles as cimgt
    except ImportError:
        err_exit(
            'Cartopy is not installed. '
            'Please install it to plot the catalog map.\n'
            'See https://scitools.org.uk/cartopy/docs/latest/installing.html'
        )
    fig = plt.figure(figsize=(10, 10))
    stamen_terrain = cimgt.Stamen('terrain-background')
    ax = fig.add_subplot(1, 1, 1, projection=stamen_terrain.crs)
    extent = _get_map_extent(config)
    ax.set_extent(extent)
    tile_scale = _get_tile_scale(extent)
    ax.add_image(stamen_terrain, tile_scale)
    ax.coastlines(resolution='10m', edgecolor='black', linewidth=1)
    ax.add_feature(
        ccrs.cartopy.feature.BORDERS, edgecolor='black', linewidth=1)
    g_kwargs = dict(draw_labels=True, dms=True, x_inline=False, y_inline=False)
    ax.gridlines(**g_kwargs)

    def redraw_gridlines(ax):
        ax.gridlines(**g_kwargs)
    ax.callbacks.connect('xlim_changed', lambda ax: redraw_gridlines(ax))
    events = read_events_from_db(config)
    scale = config['args'].scale
    plot_version_number = config['args'].allversions
    _plot_events(ax, events, scale, plot_version_number)
    ax.set_title(get_catalog_stats(config))
    plt.show()

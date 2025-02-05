# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events in 3D using Plotly.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np
from .plot_map_utils import get_map_extent
from ..utils import err_exit
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    err_exit(
        'Plotly is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://plotly.com/python/getting-started/'
    )
try:
    from pyproj import Proj
except ImportError:
    err_exit(
        'Pyproj is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://pyproj4.github.io/pyproj/stable/installation.html'
    )


def _get_marker_sizes(events, scale):
    """
    Get the marker sizes for the events.
    Returns the events for which a size could be computed and the radii.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param scale: scale factor for the marker sizes
    :type scale: float

    :returns: events, radii
    :rtype: tuple of list
    """
    mags = [e['mag'] for e in events if e['mag'] is not None]
    # use fixed radius if no magnitudes are available
    fixed_radius = not mags
    marker_scale = scale
    if not fixed_radius:
        # remove events with no magnitude
        events = [e for e in events if e['mag'] is not None]
        radii = [np.exp(e['mag']) * marker_scale for e in events]
    else:
        radii = None
    return events, radii


def _utmzone(lon, lat):
    """
    Get the UTM zone from the longitude and latitude.

    :param lon: longitude
    :type lon: float
    :param lat: latitude
    :type lat: float

    :returns: UTM zone
    :rtype: int
    :raises ValueError: if the longitude is out of range
    """
    # Special Cases for Norway & Svalbard
    if 55 < lat < 64 and 2 < lon < 6:
        return 32
    if lat > 71:
        if 6 <= lon < 9:
            return 31
        if 9 <= lon < 12:
            return 33
        if 18 <= lon < 21:
            return 33
        if 21 <= lon < 24:
            return 35
        if 30 <= lon < 33:
            return 35
    # Rest of the world
    if -180 <= lon <= 180:
        return (int((lon + 180) // 6) % 60) + 1
    raise ValueError('Longitude out of range')


def _map_projection(events, config):
    """
    Project the events on a map using UTM coordinates.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj

    :returns: xcoords, ycoords, extent
    :rtype: tuple
    """
    lonlat_extent = get_map_extent(events, config)
    utm_zone = _utmzone(
        (lonlat_extent[0] + lonlat_extent[1]) / 2,
        (lonlat_extent[2] + lonlat_extent[3]) / 2
    )
    to_utm = Proj(proj='utm', zone=utm_zone, ellps='WGS84')
    lons = [e['lon'] for e in events]
    lats = [e['lat'] for e in events]
    xcoords, ycoords = to_utm(lons, lats)
    xcoords = np.array(xcoords) / 1e3
    ycoords = np.array(ycoords) / 1e3
    # convert extent to UTM
    x0, y0 = to_utm(lonlat_extent[0], lonlat_extent[2])
    x1, y1 = to_utm(lonlat_extent[1], lonlat_extent[3])
    x0 /= 1e3
    y0 /= 1e3
    x1 /= 1e3
    y1 /= 1e3
    x_mean = (x0 + x1) / 2
    y_mean = (y0 + y1) / 2
    x0 -= x_mean
    x1 -= x_mean
    y0 -= y_mean
    y1 -= y_mean
    xcoords -= x_mean
    ycoords -= y_mean
    return xcoords, ycoords, (x0, x1, y0, y1)


def plot_catalog_map_with_plotly(events, config):
    """
    Plot the catalog map using plotly

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj
    """
    events, radii = _get_marker_sizes(events, config['args'].scale)
    xcoords, ycoords, extent = _map_projection(events, config)
    evids = [e['evid'] for e in events]
    times = [e['time'] for e in events]
    lons = [e['lon'] for e in events]
    lats = [e['lat'] for e in events]
    depths = [e['depth'] for e in events]
    mags = [e['mag'] for e in events]
    hover_data = {
        'evid': evids, 'time': times,
        'lon': lons, 'lat': lats, 'depth': depths,
        'mag': mags
    }
    fig = px.scatter_3d(
        x=xcoords, y=ycoords, z=depths,
        labels={'x': 'X (km)', 'y': 'Y (km)', 'z': 'Depth (km)'},
        size=radii,
        hover_data=hover_data,
    )
    if radii is None:
        fig.update_traces(marker={'size': 3})
    # Update hover to exclude "x", "y", and "size"
    fig.update_traces(hovertemplate='<br>'.join([
        'Evid: %{customdata[0]}',
        'Time: %{customdata[1]}',
        'Lon: %{customdata[2]:.3f}',
        'Lat: %{customdata[3]:.3f}',
        'Depth: %{customdata[4]:.1f} km',
        'Mag: %{customdata[5]:.1f}'
    ]))
    camera = {
        'up': {'x': 0, 'y': 0, 'z': 1},
        'center': {'x': 0, 'y': 0, 'z': 0},
        'eye': {'x': 0, 'y': -1.5, 'z': 2}
    }
    fig.update_layout(
        scene={
            'zaxis': {'autorange': 'reversed'},
            'aspectmode': 'data'
        },
        width=1200, height=800,
        scene_camera=camera
    )
    # add a rectangle to show the map extent
    x0, x1, y0, y1 = extent
    fig.add_trace(go.Scatter3d(
        x=[x0, x1, x1, x0, x0],
        y=[y0, y0, y1, y1, y0],
        z=[0, 0, 0, 0, 0],
        mode='lines',
        line={'color': 'gray', 'width': 2},
        name='bounding box'
    ))
    fig.show()

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
import warnings
import os
from zipfile import ZipFile
import requests
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
try:
    import shapefile
    import shapely
except ImportError:
    err_exit(
        'Pyshp and Shapely are not installed. '
        'Please install them to plot the catalog map.\n'
        'See https://pypi.org/project/pyshp/'
        'and https://pypi.org/project/Shapely/'
    )
warnings.filterwarnings('ignore', category=RuntimeWarning, module='shapely')


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


def _download_coastline(shapefile_dir):
    """
    Download the coastline shapefile from Natural Earth and extract it.

    :param shapefile_dir: directory where the shapefile will be saved
    :type shapefile_dir: str
    """
    print('Downloading coastline shapefile from Natural Earth...')
    os.makedirs(shapefile_dir, exist_ok=True)
    url = 'https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip'
    zip_path = os.path.join(shapefile_dir, 'ne_10m_coastline.zip')
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(shapefile_dir)
    os.remove(zip_path)


def _get_coastline(bounding_box=None):
    """
    Read coastline from a shapefile, clip it to a bounding box, and return it
    as a list of coordinates.

    Uses pyshp as backend.

    :param shapefile_path: Path to the shapefile.
    :type shapefile_path: str
    :param bounding_box: Bounding box to clip the coastline
        (lon_min, lon_max, lat_min, lat_max).
    :type bounding_box: tuple or None

    :returns: clipped coastline coordinates.
    :rtype: list
    """
    shapefile_dir = os.path.join(
        os.path.expanduser('~'), '.seiscat', 'shapefiles')
    shapefile_path = os.path.join(shapefile_dir, 'ne_10m_coastline.shp')
    if not os.path.exists(shapefile_path):
        _download_coastline(shapefile_dir)
    if bounding_box is not None:
        lon_min, lon_max, lat_min, lat_max = bounding_box
    else:
        lon_min, lon_max, lat_min, lat_max = -180, 180, -90, 90
    bounding_box = shapely.geometry.box(lon_min, lat_min, lon_max, lat_max)
    sf = shapefile.Reader(shapefile_path)
    clipped_coastline = []
    for feature in sf.shapeRecords():
        geom = shapely.geometry.shape(feature.shape.__geo_interface__)
        clipped_geom = geom.intersection(bounding_box)
        if clipped_geom.is_empty:
            continue
        if clipped_geom.geom_type == 'LineString':
            clipped_coastline.append(list(clipped_geom.coords))
        elif clipped_geom.geom_type == 'MultiLineString':
            clipped_coastline.extend(
                list(line.coords) for line in clipped_geom.geoms)
    return clipped_coastline


def _map_projection(events, config):
    """
    Project the events on a map using UTM coordinates.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj

    :returns: xcoords, ycoords, extent, coast_km
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
    coast = _get_coastline(bounding_box=lonlat_extent)
    coast_km = [
        (np.array(to_utm(*zip(*line))[0]) / 1e3 - x_mean,
         np.array(to_utm(*zip(*line))[1]) / 1e3 - y_mean)
        for line in coast
    ]
    return xcoords, ycoords, (x0, x1, y0, y1), coast_km


def plot_catalog_map_with_plotly(events, config):
    """
    Plot the catalog map using plotly

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj
    """
    events, radii = _get_marker_sizes(events, config['args'].scale)
    xcoords, ycoords, extent, coast = _map_projection(events, config)
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
    # Combine all coastline segments into a single trace
    x_coast = []
    y_coast = []
    z_coast = []
    for x, y in coast:
        x_coast.extend(x)
        y_coast.extend(y)
        z_coast.extend([0] * len(x))
        # Add `None` to create breaks between segments
        x_coast.append(None)
        y_coast.append(None)
        z_coast.append(None)
    # Add the combined coastline trace to the plot
    fig.add_trace(go.Scatter3d(
        x=x_coast, y=y_coast, z=z_coast,
        mode='lines',
        line={'color': 'black', 'width': 1},
        name='coastline'
    ))
    fig.show()

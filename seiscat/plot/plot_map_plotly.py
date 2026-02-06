# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events in 3D using Plotly.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
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
    if not fixed_radius:
        # remove events with no magnitude
        events = [e for e in events if e['mag'] is not None]
        radii = [np.exp(e['mag']) for e in events]
        radii = np.array(radii)/np.max(radii) * scale * 3
    else:
        radii = scale/3
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


def _add_coastline_and_extent(fig, extent, coast):
    """
    Add the coastline and the map extent to the figure.
    """
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


def _add_time_slider(fig, xcoords, ycoords, depths, radii, times):
    """
    Add a time slider to the figure.
    """
    def _scatter3d(xcoords, ycoords, depths, radii):
        return go.Scatter3d(
            x=xcoords,
            y=ycoords,
            z=depths,
            mode='markers',
            marker={'size': radii}
        )
    time_step = 1 if len(times) < 100 else len(times) // 100
    frames = [
        go.Frame(
            data=[_scatter3d(
                xcoords[:i+1], ycoords[:i+1], depths[:i+1],
                radii[:i+1] if isinstance(radii, (list, np.ndarray)) else radii
            )],
            name=f'frame{i}'
        )
        for i in range(0, len(times), time_step)
    ]
    fig.update(frames=frames)
    fig.update_layout(
        updatemenus=[
            {
                'buttons': [
                    {
                        'args': [
                            None, {
                                'frame': {'duration': 100, 'redraw': True},
                                'fromcurrent': True,
                                'transition': {'duration': 100}
                            }
                        ],
                        'label': 'Play',
                        'method': 'animate'
                    },
                    {
                        'args': [
                            [None], {
                                'frame': {'duration': 0, 'redraw': True},
                                'mode': 'immediate',
                                'transition': {'duration': 0}
                                }
                        ],
                        'label': 'Pause',
                        'method': 'animate'
                    }
                ],
                'direction': 'left',
                'pad': {'r': 10, 't': 87},
                'showactive': False,
                'type': 'buttons',
                'x': 0.1,
                'xanchor': 'right',
                'y': 0,
                'yanchor': 'top'
            }
        ],
        sliders=[{
            'active': 0,
            'yanchor': 'top',
            'xanchor': 'left',
            'currentvalue': {
                'font': {'size': 20},
                'prefix': 'Time:',
                'visible': True,
                'xanchor': 'right'
            },
            'transition': {'duration': 300, 'easing': 'cubic-in-out'},
            'pad': {'b': 10, 't': 50},
            'len': 0.9,
            'x': 0.1,
            'y': 0,
            'steps': [{
                'args': [
                    [f'frame{i}'], {
                        'frame': {'duration': 300, 'redraw': True},
                        'mode': 'immediate',
                        'transition': {'duration': 300}
                    }
                ],
                'label': f'{times[i]}',
                'method': 'animate'
            } for i in range(0, len(times), time_step)]
        }]
    )


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
    # if depth is None, use 0
    depths = [e['depth'] if e['depth'] is not None else 0 for e in events]
    hover_data = {
        'evid': evids, 'time': times,
        'lon': lons, 'lat': lats, 'depth': depths
    }
    hover_template_list = [
        'Evid: %{customdata[0]}',
        'Time: %{customdata[1]}',
        'Lon: %{customdata[2]:.3f}',
        'Lat: %{customdata[3]:.3f}',
        'Depth: %{customdata[4]:.1f} km'
    ]
    mags = [e['mag'] for e in events]
    # if not all mags are None, add them to the hover data
    if any(mags):
        hover_data['mag'] = mags
        hover_template_list.append('Mag: %{customdata[5]:.1f}')
    if isinstance(radii, (list, np.ndarray)):
        size = radii
        size_max = np.max(radii)
    else:
        size = size_max = None
    fig = px.scatter_3d(
        x=xcoords, y=ycoords, z=depths,
        labels={'x': 'X (km)', 'y': 'Y (km)', 'z': 'Depth (km)'},
        size=size,
        size_max=size_max,
        hover_data=hover_data
    )
    if size is None:
        fig.update_traces(marker={'size': radii})
    # Remove borders from markers
    fig.update_traces(marker={'line': {'width': 0}})
    # Update hover to exclude "x", "y", and "size"
    fig.update_traces(hovertemplate='<br>'.join(hover_template_list))
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
    _add_coastline_and_extent(fig, extent, coast)
    if config['args'].time_slider:
        _add_time_slider(fig, xcoords, ycoords, depths, radii, times)
    fig.show()

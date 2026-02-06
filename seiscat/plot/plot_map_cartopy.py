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
import os
import json
import urllib.request
import zipfile
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
from .plot_map_utils import get_map_extent
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit
try:
    import cartopy
    import cartopy.crs as ccrs
except ImportError:
    err_exit(
        'Cartopy is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://scitools.org.uk/cartopy/docs/latest/installing.html'
    )


def _convert_geotiff_to_png(geotiff_file, png_file):
    """
    Convert a GeoTIFF file to PNG format.

    :param geotiff_file: path to the input GeoTIFF file
    :param png_file: path to the output PNG file
    """
    print('Converting Natural Earth imagery to PNG (this may take a while)...')
    # Increase the limit to handle large images
    Image.MAX_IMAGE_PIXELS = None
    img = Image.open(geotiff_file)
    img.save(png_file, 'PNG')
    print('Conversion completed.')


def _download_natural_earth_imagery():
    """
    Download and cache Natural Earth imagery if not already present.
    Sets up environment variable for Cartopy background images.

    :returns: path to the backgrounds directory
    """
    data_dir = cartopy.config['data_dir']
    cache_dir = os.path.join(data_dir, 'raster', 'natural_earth')
    os.makedirs(cache_dir, exist_ok=True)

    geotiff_file = os.path.join(cache_dir, 'NE1_HR_LC_SR_W_DR.tif')
    png_file = os.path.join(cache_dir, 'NE1_HR_LC_SR_W_DR.png')
    images_json_file = os.path.join(cache_dir, 'images.json')

    # Check if PNG file and JSON file already exist
    if os.path.exists(png_file) and os.path.exists(images_json_file):
        print('Using cached Natural Earth imagery...')
        return cache_dir

    # Download the file if TIFF and PNG files are not present
    if not os.path.exists(geotiff_file) and not os.path.exists(png_file):
        url = (
            'https://naciscdn.org/naturalearth/'
            '10m/raster/NE1_HR_LC_SR_W_DR.zip'
        )
        zip_file = os.path.join(cache_dir, 'NE1_HR_LC_SR_W_DR.zip')

        print('Downloading Natural Earth imagery (this may take a while)...')
        try:
            urllib.request.urlretrieve(url, zip_file)
            print('Extracting Natural Earth imagery...')
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(cache_dir)
            os.remove(zip_file)
            print('Natural Earth imagery cached successfully.')
        except (urllib.error.URLError, zipfile.BadZipFile) as e:
            print(f'Failed to download Natural Earth imagery: {e}')
            return cache_dir

    # Convert TIFF to PNG if needed
    if os.path.exists(geotiff_file) and not os.path.exists(png_file):
        try:
            _convert_geotiff_to_png(geotiff_file, png_file)
            # Remove the TIFF file after successful conversion
            if os.path.exists(png_file):
                os.remove(geotiff_file)
                # Also remove any auxiliary files from the zip extraction
                for ext in ['.tfw', '.prj', '.VERSION.txt', '.README.html']:
                    aux_file = os.path.join(
                        cache_dir, f'NE1_HR_LC_SR_W_DR{ext}'
                    )
                    if os.path.exists(aux_file):
                        os.remove(aux_file)
                print('Cleaned up auxiliary files after conversion.')
        except ImportError:
            print('Warning: PIL not available. '
                  'Cannot convert TIFF to PNG for background image.')
        except (OSError, IOError) as e:
            print(f'Warning: Could not convert TIFF to PNG: {e}')

    # Create images.json for Cartopy
    if not os.path.exists(images_json_file):
        images_config = {
            '__comment__': 'JSON file for Cartopy background images',
            'NaturalEarthRelief': {
                '__comment__': 'Natural Earth I with shaded Relief',
                '__source__': (
                    'https://naciscdn.org/naturalearth/'
                    '10m/raster/NE1_HR_LC_SR_W_DR.zip'
                ),
                '__projection__': 'PlateCarree',
                'high': 'NE1_HR_LC_SR_W_DR.png'
            }
        }
        try:
            with open(images_json_file, 'w', encoding='utf-8') as f:
                json.dump(images_config, f, indent=2)
            print(
                'Created background images configuration at '
                f'{images_json_file}'
            )
        except (OSError, IOError) as e:
            print(f'Warning: Could not create images.json: {e}')

    return cache_dir


def _add_simple_background(ax):
    """
    Add a simple background to the map.

    :param ax: matplotlib axes object
    """
    ax.add_feature(ccrs.cartopy.feature.LAND, facecolor='wheat')
    ax.add_feature(ccrs.cartopy.feature.OCEAN, facecolor='lightblue')


def _add_natural_earth_background(ax, extent):
    """
    Add Natural Earth imagery to the map using Cartopy's background_img method.

    :param ax: matplotlib axes object
    :param extent: map extent (lon_min, lon_max, lat_min, lat_max)
    """
    # Set up the background images directory
    backgrounds_dir = _download_natural_earth_imagery()
    os.environ['CARTOPY_USER_BACKGROUNDS'] = backgrounds_dir

    # add a small padding to the extent to ensure
    # the background image covers the entire area
    lon_min, lon_max, lat_min, lat_max = extent
    lon_padding = (lon_max - lon_min) * 0.1
    lat_padding = (lat_max - lat_min) * 0.1
    extent = (
        max(-180, lon_min - lon_padding),
        min(180, lon_max + lon_padding),
        max(-90, lat_min - lat_padding),
        min(90, lat_max + lat_padding)
    )

    try:
        ax.background_img(
            name='NaturalEarthRelief',
            resolution='high',
            extent=extent
        )
    except (OSError, IOError, KeyError, ValueError, AttributeError) as e:
        print(f'Warning: Could not load Natural Earth background image ({e}). '
              'Using simple background.')
        _add_simple_background(ax)


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
    extent = get_map_extent(events, config)
    ax.set_extent(extent)
    _add_natural_earth_background(ax, extent)
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

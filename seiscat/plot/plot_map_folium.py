# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map using folium.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import webbrowser
import tempfile
from .plot_map_utils import get_map_extent
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit
try:
    import folium
    import branca
except ImportError:
    err_exit(
        'Folium is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://python-visualization.github.io/folium/installing.html'
    )


def plot_catalog_map_with_folium(events, config):
    """
    Plot the catalog map with folium.

    :param config: config object
    """
    # Get map extent
    lon_min, lon_max, lat_min, lat_max = get_map_extent(events, config)
    # Plot map
    m = folium.Map(
        location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
        zoom_start=5,
        tiles=None
    )
    # Add tiles and layer control
    folium.TileLayer(
        name='CartoDB Positron',
        tiles='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">'
             'OpenStreetMap</a> contributors &copy; '
             '<a href="https://carto.com/attributions">CARTO</a>',
    ).add_to(m)
    folium.TileLayer(
        name='Esri World Imagery',
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/'
              'World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, '
             'AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, '
             'and the GIS User Community'
    ).add_to(m)
    folium.TileLayer(
        name='Esri World Topo Map',
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/'
              'World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, '
             'Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, '
             'Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), '
             'and the GIS User Community'
    ).add_to(m)
    folium.LayerControl().add_to(m)
    m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])
    # Add catalog stats to the map
    catalog_stats = get_catalog_stats(config)
    branca_element = branca.element.Element(catalog_stats)
    m.get_root().html.add_child(branca_element)
    # Add events to the map
    mags = [event['mag'] for event in events if event['mag'] is not None]
    # If no magnitudes are available, use a fixed marker radius
    fixed_radius = not mags
    scale = config['args'].scale
    marker_scale = 0.2 * scale
    for event in events:
        if fixed_radius:
            radius = marker_scale
        elif event['mag'] is None:
            continue
        else:
            radius = 1.5**(event['mag'])*marker_scale
        mag_str = (
            f"{event['mag_type']} {event['mag']:.1f} <br>"
            if event['mag'] is not None else ''
        )
        popup_text = folium.Html(
            f"<b>{event['evid']} v{event['ver']}</b> <br>"
            f"{mag_str}"
            f"{event['time']} <br>"
            f"{event['lat']:.2f} {event['lon']:.2f} "
            f"{event['depth']:.1f} km",
            script=True
        )
        popup = folium.Popup(popup_text, min_width=200, max_width=200)
        folium.CircleMarker(
            location=[event['lat'], event['lon']],
            radius=radius,
            color='red',
            fill=True,
            fill_color='red',
            popup=popup
        ).add_to(m)
    # Add map extent
    folium.Rectangle(
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        color='gray',
        fill=False
    ).add_to(m)
    # Save map to temporary file and open it in the browser
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        m.save(f.name)
        file_uri = f'file://{f.name}'
        webbrowser.open_new(file_uri)

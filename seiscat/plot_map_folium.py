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
from .db import read_events_from_db, get_catalog_stats
from .utils import err_exit
from .plot_map_utils import get_map_extent
try:
    import folium
    import branca
except ImportError:
    err_exit(
        'Folium is not installed. '
        'Please install it to plot the catalog map.\n'
        'See https://python-visualization.github.io/folium/installing.html'
    )


def plot_catalog_map_with_folium(config):
    """
    Plot the catalog map with folium.

    :param config: config object
    """
    # Read events from DB
    events = read_events_from_db(config)
    if len(events) == 0:
        err_exit('No events found in the database.')
    # Get map extent
    lon_min, lon_max, lat_min, lat_max = get_map_extent(config)
    if None in (lon_min, lon_max, lat_min, lat_max):
        err_exit(
            'Map extent not defined. '
            'Please define it in the config file.'
        )
    # Plot map
    m = folium.Map(
        location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
        zoom_start=5,
        tiles='OpenStreetMap'
    )
    m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])
    # Add catalog stats to the map
    catalog_stats = get_catalog_stats(config)
    branca_element = branca.element.Element(catalog_stats)
    m.get_root().html.add_child(branca_element)
    # Add events to the map
    scale = config['args'].scale
    marker_scale = 0.2 * scale
    for event in events:
        popup_text = folium.Html(
            f"<b>{event['evid']} v{event['ver']}</b> <br>"
            f"{event['mag_type']} {event['mag']:.1f} <br>"
            f"{event['time']} <br>"
            f"{event['lat']:.2f} {event['lon']:.2f} "
            f"{event['depth']:.1f} km",
            script=True
        )
        popup = folium.Popup(popup_text, min_width=200, max_width=200)
        folium.CircleMarker(
            location=[event['lat'], event['lon']],
            radius=1.5**(event['mag'])*marker_scale,
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

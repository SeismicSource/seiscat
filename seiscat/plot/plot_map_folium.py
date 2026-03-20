# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map using folium.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import webbrowser
import tempfile
import math
from .plot_map_utils import get_map_extent
from .plot_utils import (
    get_event_popup_html, get_event_color_values, get_label_for_attribute,
    get_colormap_hex_colors, get_time_colorbar_ticks,
)
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


def _validate_output_file(out_file):
    """Validate output target and print an operation banner."""
    if out_file:
        if not out_file.endswith('.html'):
            err_exit(
                'Output file for folium maps should have a .html extension')
        print(f'Saving map to {out_file}...')
    else:
        print('Building map...')


def _create_map(extent):
    """Create a folium map centered on the requested extent."""
    lon_min, lon_max, lat_min, lat_max = extent
    return folium.Map(
        location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2],
        zoom_start=5,
        tiles=None,
    )


def _add_tile_layers(m):
    """Add base tiles and controls."""
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


def _add_catalog_stats(m, config):
    """Render catalog stats in the map HTML container."""
    catalog_stats = get_catalog_stats(config)
    branca_element = branca.element.Element(catalog_stats)
    m.get_root().html.add_child(branca_element)


def _build_colorbar_css():
    """Return CSS that improves colorbar readability."""
    return (
        '<style>'
        '.legend.leaflet-control { '
        'overflow: visible !important; '
        'padding-bottom: 26px; '
        '} '
        '.legend.leaflet-control svg { '
        'overflow: visible !important; '
        '} '
        '#legend text { '
        'font-size: 14px !important; '
        'paint-order: stroke; '
        'stroke: #ffffff; '
        'stroke-width: 2.5px; '
        'stroke-linejoin: round; '
        '} '
        '#legend .caption { '
        'font-size: 16px !important; '
        'font-weight: 600; '
        'paint-order: stroke; '
        'stroke: #ffffff; '
        'stroke-width: 3px; '
        'stroke-linejoin: round; '
        'transform: translateX(8px); '
        '} '
        '</style>'
    )


def _build_time_colorbar_label_script():
    """Return JS that formats numeric legend ticks as UTC datetimes."""
    return (
        '<script>'
        '(function () {'
        'function pad(v) { return String(v).padStart(2, "0"); }'
        'function formatUtc(sec) {'
        '  var d = new Date(sec * 1000);'
        '  return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + '
        '    pad(d.getUTCDate());'
        '}'
        'function relabel() {'
        '  var legend = document.getElementById("legend");'
        '  if (!legend) { return false; }'
        '  var ticks = legend.querySelectorAll(".tick text");'
        '  if (!ticks.length) { return false; }'
        '  ticks.forEach(function (node) {'
        '    var txt = (node.textContent || "").trim();'
        '    var val = Number(txt.replace(/,/g, ""));'
        '    if (Number.isFinite(val)) {'
        '      node.textContent = formatUtc(val);'
        '      var x = Number(node.getAttribute("x") || 0);'
        '      var y = Number(node.getAttribute("y") || 0);'
        '      node.setAttribute("transform", "rotate(-28 " + x + " " + '
        '        y + ")");'
        '      node.setAttribute("text-anchor", "end");'
        '    }'
        '  });'
        '  return true;'
        '}'
        'function scheduleRelabel() {'
        '  var attempts = 0;'
        '  var timer = setInterval(function () {'
        '    attempts += 1;'
        '    if (relabel() || attempts > 40) { clearInterval(timer); }'
        '  }, 100);'
        '}'
        'if (document.readyState === "loading") {'
        '  document.addEventListener("DOMContentLoaded", scheduleRelabel);'
        '} else {'
        '  scheduleRelabel();'
        '}'
        'if (typeof MutationObserver !== "undefined") {'
        '  var obs = new MutationObserver(function () { relabel(); });'
        '  obs.observe(document.documentElement, { childList: true, '
        '    subtree: true });'
        '  setTimeout(function () { obs.disconnect(); }, 10000);'
        '}'
        '})();'
        '</script>'
    )


def _build_colormap(m, events, args):
    """Build and attach a folium colormap if --colorby is enabled."""
    colorby = getattr(args, 'colorby', None)
    if colorby is None:
        return colorby, None

    color_values_list = get_event_color_values(events, colorby)
    if color_values_list is None:
        return colorby, None

    vmin = min(color_values_list)
    vmax = max(color_values_list)
    if vmin == vmax:
        vmax = vmin + 1
    colors = get_colormap_hex_colors(getattr(args, 'colormap', None))
    folium_colormap = branca.colormap.LinearColormap(
        colors,
        vmin=vmin, vmax=vmax,
        caption=get_label_for_attribute(colorby)
    )
    if colorby == 'time':
        # Branca expects numeric tick labels for axis placement.
        # Keep numeric ticks, then rewrite displayed text with JS.
        tickvals, _ticktext = get_time_colorbar_ticks(
            color_values_list,
            multiline=False,
        )
        folium_colormap.tick_labels = tickvals
    # Make the legend bar thicker than the branca defaults.
    folium_colormap.width = 520
    folium_colormap.height = 96 if colorby == 'time' else 64
    folium_colormap.add_to(m)
    m.get_root().header.add_child(
        branca.element.Element(_build_colorbar_css())
    )
    if colorby == 'time':
        m.get_root().header.add_child(
            branca.element.Element(_build_time_colorbar_label_script())
        )
    return colorby, folium_colormap


def _add_events(m, events, scale, colorby, folium_colormap):
    """Add event markers to the map."""
    mags = [event['mag'] for event in events if event['mag'] is not None]
    fixed_radius = not mags
    marker_scale = 0.2 * scale
    for event in events:
        if fixed_radius:
            radius = marker_scale
        elif event['mag'] is None:
            continue
        else:
            radius = 1.5**(event['mag']) * marker_scale
        popup_text = folium.Html(
            get_event_popup_html(event),
            script=True
        )
        popup = folium.Popup(popup_text, min_width=260, max_width=260)
        if folium_colormap is not None:
            val = event.get(colorby)
            try:
                numeric_val = float(val)
                if math.isnan(numeric_val):
                    raise ValueError('NaN color value')
            except (TypeError, ValueError):
                numeric_val = folium_colormap.vmin
            event_color = folium_colormap(numeric_val)
        else:
            event_color = 'red'
        folium.CircleMarker(
            location=[event['lat'], event['lon']],
            radius=radius,
            color=event_color,
            fill=True,
            fill_color=event_color,
            popup=popup
        ).add_to(m)


def _add_map_extent_rectangle(m, extent):
    """Draw extent rectangle on top of the map."""
    lon_min, lon_max, lat_min, lat_max = extent
    folium.Rectangle(
        bounds=[[lat_min, lon_min], [lat_max, lon_max]],
        color='gray',
        fill=False
    ).add_to(m)


def _save_or_open_map(m, out_file):
    """Write the HTML map file or open a temporary browser page."""
    if out_file:
        m.save(out_file)
        print(f'Map saved to {out_file}')
    else:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            m.save(f.name)
            file_uri = f'file://{f.name}'
            webbrowser.open_new(file_uri)


def plot_catalog_map_with_folium(events, config):
    """
    Plot the catalog map with folium.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param config: config object
    :type config: configspec.ConfigObj
    """
    args = config['args']
    out_file = args.out_file
    _validate_output_file(out_file)

    extent = get_map_extent(events, config)
    m = _create_map(extent)
    _add_tile_layers(m)
    lon_min, lon_max, lat_min, lat_max = extent
    m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

    _add_catalog_stats(m, config)
    colorby, folium_colormap = _build_colormap(m, events, args)
    _add_events(m, events, args.scale, colorby, folium_colormap)
    _add_map_extent_rectangle(m, extent)
    _save_or_open_map(m, out_file)

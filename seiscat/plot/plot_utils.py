# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Utility functions shared by map and timeline plot modules.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from html import escape
import math
from datetime import datetime, timezone

DEFAULT_COLORMAP = 'viridis'


def _is_missing_plot_value(value):
    """Return True when a plot-critical numeric field is undefined."""
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _get_event_identifier(event):
    """Return a compact identifier for skip messages."""
    if event.get('evid') not in (None, ''):
        return str(event['evid'])
    if event.get('ver') not in (None, ''):
        return str(event['ver'])
    if event.get('time') is not None:
        return str(event['time'])
    # sourcery skip: reintroduce-else
    return '?'


def filter_events_for_plotting(events, backend_name=None, require_depth=False):
    """
    Filter out events with missing plot-critical coordinates or depth.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param backend_name: backend label to include in skip messages
    :type backend_name: str or None
    :param require_depth: if True, also require a defined depth value
    :type require_depth: bool

    :returns: filtered events
    :rtype: list
    """
    filtered_events = []
    backend_suffix = (
        f' for {backend_name} backend' if backend_name is not None else ''
    )
    for event in events:
        reasons = []
        if any(
            _is_missing_plot_value(event.get(field_name))
            for field_name in ('lat', 'lon')
        ):
            reasons.append('latitude/longitude are not both defined')
        if require_depth and _is_missing_plot_value(event.get('depth')):
            reasons.append('depth is not defined')
        if reasons:
            event_id = _get_event_identifier(event)
            print(
                f'Skipping event "{event_id}"{backend_suffix}: '
                f'{" and ".join(reasons)}.'
            )
            continue
        filtered_events.append(event)
    return filtered_events


def format_epoch_seconds(value, multiline=False):
    """Format Unix seconds to a compact UTC datetime label."""
    dt = datetime.fromtimestamp(value, tz=timezone.utc)
    fmt = '%Y-%m-%d\n%H:%M' if multiline else '%Y-%m-%d %H:%M'
    return dt.strftime(fmt)


def get_time_colorbar_ticks(values, multiline=False):
    """Return evenly spaced tick values and datetime labels for time scales."""
    v_min = min(values)
    v_max = max(values)
    if v_min == v_max:
        tickvals = [v_min]
    else:
        tickvals = [v_min + i * (v_max - v_min) / 4 for i in range(5)]
    ticktext = [
        format_epoch_seconds(value, multiline=multiline)
        for value in tickvals
    ]
    return tickvals, ticktext


def get_plotly_time_colorbar_kwargs(values):
    """Return Plotly colorbar kwargs for numeric epoch-second values."""
    tickvals, ticktext = get_time_colorbar_ticks(values, multiline=False)
    return {
        'tickmode': 'array',
        'tickvals': tickvals,
        'ticktext': ticktext,
    }


def get_label_for_attribute(attribute):
    """Return a human-readable label for a known event attribute."""
    labels = {
        'time': 'Time',
        'mag': 'Magnitude',
        'depth': 'Depth (km)',
        'lat': 'Latitude (°)',
        'lon': 'Longitude (°)',
    }
    return labels.get(attribute, attribute)


def _format_event_field_value(field_name, field_value):
    """Format one event field value for popups/hover labels."""
    if field_value is None:
        return 'None'
    if isinstance(field_value, float):
        if field_name in ('lat', 'lon'):
            return f'{field_value:.4f}'
        if field_name == 'depth':
            return f'{field_value:.2f} km'
        precision = 1 if field_name == 'mag' else None
        return (
            f'{field_value:.{precision}f}'
            if precision is not None else f'{field_value:.6g}'
        )
    return str(field_value)


def get_event_popup_html(event):
    """Build a popup/hover HTML string with all event fields."""
    lines = []
    for field_name, field_value in event.items():
        value = _format_event_field_value(field_name, field_value)
        lines.append(
            f'<b>{escape(str(field_name))}</b>: {escape(value)}'
        )
    return '<br>'.join(lines)


def get_event_color_values(events, colorby):
    """
    Get numeric color values for events based on a named attribute.

    :param events: list of events, each event is a dictionary
    :type events: list
    :param colorby: attribute name to use for color, or None
    :type colorby: str or None

    :returns: list of floats (one per event) or None if colorby is None,
        not found in events, or has no numeric values
    :rtype: list of float or None
    """
    if colorby is None:
        return None
    raw = [e.get(colorby) for e in events]

    def _to_finite_float(value):
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return None if math.isnan(numeric) else numeric

    converted = [_to_finite_float(value) for value in raw]
    valid = [value for value in converted if value is not None]
    if not valid:
        print(
            f'Warning: attribute "{colorby}" has no numeric values. '
            'Using default color.'
        )
        return None
    if len(valid) < len(converted):
        print(
            f'Warning: some events have missing "{colorby}" values. '
            'Those markers will use the minimum color value.'
        )
    vmin = min(valid)
    return [value if value is not None else vmin for value in converted]


def get_matplotlib_colormap(colormap_name=None):
    """
    Return a validated Matplotlib colormap object.

    :param colormap_name: Matplotlib colormap name, or ``None``
    :type colormap_name: str or None
    :returns: ``(name, cmap)`` tuple
    :rtype: tuple
    """
    cmap_name = colormap_name or DEFAULT_COLORMAP
    try:
        from matplotlib import colormaps
    except ImportError:
        from ..utils import err_exit
        err_exit(
            'Matplotlib is required to use named colormaps. '
            'Please install it or omit --colormap.'
        )
    try:
        return cmap_name, colormaps[cmap_name]
    except KeyError:
        from ..utils import err_exit
        err_exit(
            f'Unknown Matplotlib colormap "{cmap_name}". '
            'Use a valid Matplotlib colormap name such as '
            '"viridis", "plasma", or "inferno".'
        )


def get_colormap_hex_colors(colormap_name=None, samples=16):
    """Return evenly sampled hex colors from a Matplotlib colormap."""
    _, cmap = get_matplotlib_colormap(colormap_name)
    from matplotlib.colors import to_hex
    samples = max(samples, 2)
    values = [i / (samples - 1) for i in range(samples)]
    return [to_hex(cmap(value), keep_alpha=False) for value in values]


def get_plotly_colorscale(colormap_name=None, samples=16):
    """Return a Plotly colorscale sampled from a Matplotlib colormap."""
    colors = get_colormap_hex_colors(colormap_name, samples=samples)
    if len(colors) == 1:
        return [[0.0, colors[0]], [1.0, colors[0]]]
    return [
        [index / (len(colors) - 1), color]
        for index, color in enumerate(colors)
    ]

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot catalog timeline using Plotly (interactive HTML).

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import webbrowser
import tempfile
import os
from datetime import datetime, timezone
try:
    import plotly.graph_objects as go
except ImportError:
    from ..utils import err_exit
    err_exit(
        'Plotly is not installed. '
        'Please install it to use the web backend.\n'
        'Run: pip install plotly'
    )
from .plot_timeline_utils import (
    get_event_times_values_and_events, bin_events_by_time,
    get_label_for_attribute, bin_label, get_bin_size_label,
)
from .plot_map_utils import get_event_popup_html
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit


def _format_epoch_seconds(value):
    """Format Unix seconds to a compact UTC datetime label."""
    dt = datetime.fromtimestamp(value, tz=timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M')


def _time_colorbar_kwargs(values):
    """Return plotly colorbar kwargs to display numeric seconds as datetimes."""
    v_min = min(values)
    v_max = max(values)
    if v_min == v_max:
        tickvals = [v_min]
    else:
        tickvals = [v_min + i * (v_max - v_min) / 4 for i in range(5)]
    ticktext = [_format_epoch_seconds(v) for v in tickvals]
    return {
        'tickmode': 'array',
        'tickvals': tickvals,
        'ticktext': ticktext,
    }


def _build_attribute_figure(events, args):
    """
    Build a Plotly figure for attribute-vs-time scatter.

    :param events: EventList of Event dicts
    :param args: parsed command-line arguments
    :returns: plotly Figure
    """
    attribute = args.attribute
    data = get_event_times_values_and_events(events, attribute)
    if not data:
        err_exit(
            f'No events with a valid numeric value for attribute '
            f'"{attribute}".'
        )
    times = [item[0] for item in data]
    values = [item[1] for item in data]
    source_events = [item[2] for item in data]
    hover_texts = [get_event_popup_html(event) for event in source_events]

    color_attr = getattr(args, 'colorby', None) or attribute
    label = get_label_for_attribute(attribute)
    color_label = get_label_for_attribute(color_attr)

    if color_attr == attribute:
        color_values = values
    else:
        color_values = []
        for event in source_events:
            cval = event.get(color_attr)
            if cval is None:
                err_exit(
                    f'Color attribute "{color_attr}" is missing for event '
                    f'"{event.get("evid", "?")}".'
                )
            try:
                cval = float(cval)
            except (ValueError, TypeError):
                err_exit(
                    f'Color attribute "{color_attr}" must be numeric. '
                    f'Invalid value for event "{event.get("evid", "?")}".'
                )
            if cval != cval:
                err_exit(
                    f'Color attribute "{color_attr}" has NaN value for '
                    f'event "{event.get("evid", "?")}".'
                )
            color_values.append(cval)

    y_values = values
    yaxis_kwargs = {}
    if attribute == 'time':
        y_values = [
            datetime.fromtimestamp(v, tz=timezone.utc)
            for v in values
        ]
        yaxis_kwargs = {'tickformat': '%Y-%m-%d<br>%H:%M'}

    colorbar_kwargs = {'title': color_label}
    if color_attr == 'time':
        colorbar_kwargs |= _time_colorbar_kwargs(color_values)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(times),
        y=list(y_values),
        mode='markers',
        marker=dict(
            size=8,
            color=list(color_values),
            colorscale='Viridis',
            showscale=True,
            colorbar=colorbar_kwargs,
            opacity=0.8,
        ),
        text=hover_texts,
        hovertemplate='%{text}<extra></extra>',
    ))
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=label,
        title=f'{label} vs. Time (color: {color_label})',
        yaxis=yaxis_kwargs,
    )
    return fig


def _build_count_figure(events, args):
    """
    Build a Plotly figure for event-count bar chart.

    :param events: EventList of Event dicts
    :param args: parsed command-line arguments
    :returns: plotly Figure
    """
    bins_spec = getattr(args, 'bins', None)
    bins = bin_events_by_time(events, bins_spec)
    if not bins:
        err_exit('No events to plot.')
    bin_size_label = get_bin_size_label(bins, bins_spec)

    bin_centers = [s + (e - s) / 2 for s, e in [(b[0], b[1]) for b in bins]]
    counts = [b[2] for b in bins]
    labels = [bin_label(b[0], b[1]) for b in bins]
    widths_ms = [
        (b[1] - b[0]).total_seconds() * 1000 * 0.9
        for b in bins
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bin_centers,
        y=counts,
        width=widths_ms,
        marker_color='steelblue',
        hovertemplate='%{customdata}<br>Count: %{y}<extra></extra>',
        customdata=labels,
    ))
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Event Count',
        title=f'Event Count vs. Time (bin size: {bin_size_label})',
        bargap=0,
    )
    return fig


def plot_catalog_timeline_plotly(events, config):
    """
    Plot the catalog timeline as an interactive HTML page using Plotly.

    :param events: EventList of Event dicts
    :param config: config object
    """
    args = config['args']

    if args.count:
        fig = _build_count_figure(events, args)
    else:
        fig = _build_attribute_figure(events, args)

    # Catalog stats in a figure annotation
    stats = get_catalog_stats(config)
    fig.add_annotation(
        text=stats.replace('\n', '<br>'),
        xref='paper', yref='paper',
        x=0, y=-0.18,
        showarrow=False,
        font=dict(size=10, color='grey'),
        align='left',
    )
    fig.update_layout(margin=dict(b=120))

    if out_file := getattr(args, 'out_file', None):
        fig.write_html(out_file)
        print(f'Timeline saved to {out_file}')
    else:
        # Write to a temp file and open in the default browser
        with tempfile.NamedTemporaryFile(
            suffix='.html', delete=False, mode='w', encoding='utf-8'
        ) as tmp:
            tmp_path = tmp.name
            fig.write_html(tmp_path)
        webbrowser.open(f'file://{os.path.abspath(tmp_path)}')

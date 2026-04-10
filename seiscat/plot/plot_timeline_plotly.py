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
    bin_label, get_bin_size_label, get_cumulative_event_times_and_counts,
)
from .plot_utils import (
    get_label_for_attribute, get_event_popup_html, get_plotly_colorscale,
    get_plotly_time_colorbar_kwargs,
    LARGE_N_PLOTLY_THRESHOLD, is_large_n_plotly_mode,
)
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit


def _build_attribute_figure(events, args):
    """
    Build a Plotly figure for attribute-vs-time scatter.

    :param events: EventList of Event dicts
    :param args: parsed command-line arguments
    :returns: plotly Figure
    """
    attribute = args.attribute
    color_attr = getattr(args, 'colorby', None) or attribute
    data = get_event_times_values_and_events(events, attribute, color_attr)
    if not data:
        err_exit(
            f'No events with valid values for attribute "{attribute}" '
            f'and color attribute "{color_attr}".'
        )
    times = [item[0] for item in data]
    values = [item[1] for item in data]
    source_events = [item[2] for item in data]
    large_n_mode = is_large_n_plotly_mode(len(source_events))
    if large_n_mode:
        print(
            f'Large-N mode enabled for plotly backend '
            f'({len(source_events)} events > {LARGE_N_PLOTLY_THRESHOLD}): '
            'disabling hover popups and using WebGL rendering.'
        )
    hover_texts = None
    if not large_n_mode:
        hover_texts = [get_event_popup_html(event) for event in source_events]

    label = get_label_for_attribute(attribute)
    color_label = get_label_for_attribute(color_attr)

    if color_attr == attribute:
        color_values = values
    else:
        color_values = [float(event[color_attr]) for event in source_events]

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
        colorbar_kwargs |= get_plotly_time_colorbar_kwargs(color_values)
    colorscale = get_plotly_colorscale(getattr(args, 'colormap', None))

    fig = go.Figure()
    # Scattergl (WebGL) is much faster for very large point clouds, but it
    # can have slightly lower visual quality/compatibility than Scatter
    # (SVG) for smaller datasets. Keep Scatter by default and switch to
    # Scattergl only in large-N mode.
    trace_cls = go.Scattergl if large_n_mode else go.Scatter
    trace_kwargs = dict(
        x=list(times),
        y=list(y_values),
        mode='markers',
        marker=dict(
            size=8,
            color=list(color_values),
            colorscale=colorscale,
            showscale=True,
            colorbar=colorbar_kwargs,
            opacity=0.8,
        ),
    )
    if large_n_mode:
        trace_kwargs['hoverinfo'] = 'skip'
        trace_kwargs['hovertemplate'] = None
    else:
        trace_kwargs['text'] = hover_texts
        trace_kwargs['hovertemplate'] = '%{text}<extra></extra>'
    fig.add_trace(trace_cls(**trace_kwargs))
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=label,
        title=f'{label} vs. Time (color: {color_label})',
        yaxis=yaxis_kwargs,
    )
    return fig


def _build_count_figure(events, args):
    """
    Build a Plotly figure for event-count bar chart with optional overlay.

    Modes:
    - Count only: histogram of binned events
    - Both count and cumulative: dual-axis with histogram and cumulative

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
        name='Event Count',
        width=widths_ms,
        marker_color='steelblue',
        hovertemplate='%{customdata}<br>Count: %{y}<extra></extra>',
        customdata=labels,
    ))

    title = f'Event Count vs. Time (bin size: {bin_size_label})'
    layout_kwargs = {}

    # Dual-axis mode: overlay raw-event cumulative on secondary y-axis
    if getattr(args, 'cumulative', False):
        cumulative_times, cumulative_counts = (
            get_cumulative_event_times_and_counts(events)
        )
        if not cumulative_times:
            err_exit('No events to plot.')
        fig.add_trace(go.Scatter(
            x=cumulative_times,
            y=cumulative_counts,
            mode='lines',
            name='Cumulative Count',
            line=dict(color='firebrick', width=2, shape='hv'),
            yaxis='y2',
            hovertemplate='%{x|%Y-%m-%d %H:%M}<br>'
                          'Cumulative: %{y}<extra></extra>',
        ))
        layout_kwargs['yaxis2'] = dict(
            title='Cumulative Event Count',
            overlaying='y',
            side='right',
            rangemode='tozero',
            showgrid=False,
        )
        title = (
            'Event Count and Cumulative Count vs. Time '
            f'(bin size: {bin_size_label})'
        )

    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Event Count',
        title=title,
        bargap=0,
        **layout_kwargs,
    )
    return fig


def _build_cumulative_count_figure(events):
    """Build a Plotly figure for raw-event cumulative count over time."""
    times, cumulative = get_cumulative_event_times_and_counts(events)
    if not times:
        err_exit('No events to plot.')
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times,
        y=cumulative,
        mode='lines',
        name='Cumulative Count',
        line=dict(color='firebrick', width=2, shape='hv'),
        hovertemplate='%{x|%Y-%m-%d %H:%M}<br>'
                      'Cumulative: %{y}<extra></extra>',
    ))
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Cumulative Event Count',
        yaxis=dict(rangemode='tozero'),
        title='Cumulative Event Count vs. Time',
    )
    return fig


def _dispatch_count_figure(events, args):
    """Dispatch to appropriate count-mode figure builder."""
    cumulative_only = (
        getattr(args, 'cumulative', False) and not args.count
    )
    if cumulative_only:
        return _build_cumulative_count_figure(events)
    return _build_count_figure(events, args)


def plot_catalog_timeline_plotly(events, config):
    """
    Plot the catalog timeline as an interactive HTML page using Plotly.

    :param events: EventList of Event dicts
    :param config: config object
    """
    args = config['args']

    if args.count or getattr(args, 'cumulative', False):
        fig = _dispatch_count_figure(events, args)
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

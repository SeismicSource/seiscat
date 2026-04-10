# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot catalog timeline using matplotlib.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from .plot_timeline_utils import (
    get_event_times_values_and_events, bin_events_by_time,
    get_bin_size_label, ONE_DAY_SECONDS,
    get_cumulative_event_times_and_counts,
)
from .plot_utils import (
    get_label_for_attribute, get_matplotlib_colormap, format_epoch_seconds,
)
from ..database.dbfunctions import get_catalog_stats
from ..utils import err_exit


def _plot_cumulative_overlay(ax, events, bin_size_label):
    """Overlay raw-event cumulative count on a secondary y-axis."""
    ax2 = ax.twinx()
    times, cumulative = get_cumulative_event_times_and_counts(events)
    if not times:
        err_exit('No events to plot.')
    ax2.step(
        times,
        cumulative,
        where='post',
        color='firebrick',
        linewidth=1.6,
        zorder=4,
        label='Cumulative Count',
    )
    ax2.set_ylabel('Cumulative Event Count', color='firebrick')
    ax2.tick_params(axis='y', labelcolor='firebrick')
    ax2.set_ylim(bottom=0)
    title = (
        'Event Count and Cumulative Count vs. Time '
        f'(bin size: {bin_size_label})'
    )
    ax.set_title(title)


def _plot_attribute(events, args, ax):
    """
    Scatter plot of an event attribute vs. time.

    :param events: EventList of Event dicts
    :param args: parsed command-line arguments
    :param ax: matplotlib Axes
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
    values = np.array([item[1] for item in data])
    source_events = [item[2] for item in data]

    if color_attr == attribute:
        color_values = values
    else:
        color_values = np.array([
            float(event[color_attr]) for event in source_events
        ])

    _, cmap = get_matplotlib_colormap(getattr(args, 'colormap', None))

    sc = ax.scatter(
        times, values,
        s=20, alpha=0.7,
        c=color_values, cmap=cmap,
        zorder=3,
    )
    cbar = plt.colorbar(sc, ax=ax, label=get_label_for_attribute(color_attr))
    if color_attr == 'time':
        cbar.formatter = FuncFormatter(
            lambda value, _pos: format_epoch_seconds(value, multiline=True)
        )
        cbar.update_ticks()

    if attribute == 'time':
        ax.yaxis.set_major_formatter(FuncFormatter(
            lambda value, _pos: format_epoch_seconds(value, multiline=True)
        ))

    ax.set_ylabel(get_label_for_attribute(attribute))
    ax.set_title(
        f'{get_label_for_attribute(attribute)} vs. Time '
        f'(color: {get_label_for_attribute(color_attr)})'
    )


def _plot_count(events, args, ax):
    """
    Bar chart of event count per time bin, optionally with cumulative overlay.

    Modes:
    - Count only: histogram of binned events
    - Cumulative only: raw cumulative step plot
    - Both: dual-axis with histogram (left) and cumulative (right)

    :param events: EventList of Event dicts
    :param args: parsed command-line arguments
    :param ax: matplotlib Axes
    """
    count_plot = getattr(args, 'count', False)
    cumulative_plot = getattr(args, 'cumulative', False)
    cumulative_only = cumulative_plot and not count_plot

    if cumulative_only:
        # Cumulative-only mode: raw event times, no binning
        times, cumulative = get_cumulative_event_times_and_counts(events)
        if not times:
            err_exit('No events to plot.')
        ax.step(
            times,
            cumulative,
            where='post',
            color='firebrick',
            linewidth=1.6,
            zorder=4,
        )
        ax.set_ylabel('Cumulative Event Count')
        ax.set_ylim(bottom=0)
        ax.set_title('Cumulative Event Count vs. Time')
        return

    # Count mode (with or without cumulative overlay)
    bins_spec = getattr(args, 'bins', None)
    bins = bin_events_by_time(events, bins_spec)
    if not bins:
        err_exit('No events to plot.')
    bin_size_label = get_bin_size_label(bins, bins_spec)

    bin_starts = [b[0] for b in bins]
    bin_ends = [b[1] for b in bins]
    counts = [b[2] for b in bins]

    # Width and center in units of days (matplotlib float date)
    widths_days = [
        (e - s).total_seconds() / ONE_DAY_SECONDS * 0.9
        for s, e in zip(bin_starts, bin_ends)
    ]
    centers = [s + (e - s) / 2 for s, e in zip(bin_starts, bin_ends)]

    ax.bar(
        mdates.date2num(centers),
        counts,
        width=widths_days,
        color='steelblue',
        edgecolor='white',
        linewidth=0.4,
        zorder=3,
    )
    ax.xaxis_date()
    ax.set_ylabel('Event Count (per bin)')

    # Dual-axis mode: overlay cumulative on secondary y-axis
    if not cumulative_only and cumulative_plot:
        _plot_cumulative_overlay(ax, events, bin_size_label)
    else:
        ax.set_title(f'Event Count vs. Time (bin size: {bin_size_label})')


def plot_catalog_timeline_matplotlib(events, config):
    """
    Plot the catalog timeline using matplotlib.

    :param events: EventList of Event dicts
    :param config: config object
    """
    args = config['args']
    count_plot = getattr(args, 'count', False)
    cumulative_plot = getattr(args, 'cumulative', False)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

    if count_plot or cumulative_plot:
        _plot_count(events, args, ax)
    else:
        _plot_attribute(events, args, ax)

    # X-axis formatting
    ax.xaxis.set_major_formatter(
        mdates.ConciseDateFormatter(mdates.AutoDateLocator())
    )
    fig.autofmt_xdate()

    # Catalog stats as a figure text
    stats = get_catalog_stats(config)
    fig.text(
        0.01, 0.01, stats,
        fontsize=7, color='grey',
        va='bottom', ha='left',
        transform=fig.transFigure,
    )

    ax.set_xlabel('Time')
    plt.tight_layout()

    if out_file := getattr(args, 'out_file', None):
        fig.savefig(out_file, dpi=150)
        print(f'Timeline saved to {out_file}')
    else:
        plt.show()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot catalog event count over time in the terminal.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import shutil
from rich.console import Console
from rich.text import Text
from .plot_timeline_utils import (
    bin_events_by_time, bin_label, get_bin_size_label,
    get_cumulative_event_times_and_counts,
)
from ..utils import err_exit

# Block characters: ░ ▒ ▓ █  — use full block for simplicity
_BAR_CHAR = '█'
# Minimum and maximum bar widths (characters)
_MIN_BAR_COLS = 1
_MAX_LABEL_WIDTH = 18


def plot_catalog_timeline_terminal(events, config):
    """
    Print a horizontal bar chart of event count per time bin to the terminal.

    Modes:
    - Count only: shows per-bin event counts as bars
    - Cumulative only: shows raw cumulative event counts over time
    - Both: shows per-bin counts as bars plus cumulative totals

    Only count mode is supported for the terminal backend.  If the user
    selects ``--attribute`` mode the command will still show counts and print
    an informational note.

    :param events: EventList of Event dicts
    :param config: config object
    """
    args = config['args']
    bins_spec = getattr(args, 'bins', None)

    # Attribute mode is unsupported; fall back gracefully
    if not args.count:
        Console().print(
            '[yellow]Note:[/yellow] terminal backend only supports '
            'count mode. Showing event count per time bin.'
        )

    cumulative_only = (
        getattr(args, 'cumulative', False) and not args.count
    )
    if cumulative_only:
        times, cumulative = get_cumulative_event_times_and_counts(events)
        if not times:
            err_exit('No events to plot.')

        console = Console(highlight=False)
        console.print()
        console.print(
            '[bold]Cumulative event count over time[/bold] '
            f'([dim]{len(events)} events total[/dim])'
        )
        console.print()
        for dt, count in zip(times, cumulative):
            line = Text()
            line.append(dt.strftime('%Y-%m-%d %H:%M:%S'), style='cyan')
            line.append(' | ', style='dim')
            line.append(str(count), style='bold bright_blue')
            console.print(line)
        console.print()
        return

    bins = bin_events_by_time(events, bins_spec)
    if not bins:
        err_exit('No events to plot.')
    bin_size_label = get_bin_size_label(bins, bins_spec)

    counts = [b[2] for b in bins]
    max_count = max(counts, default=1)
    labels = [bin_label(b[0], b[1]) for b in bins]

    # Cumulative counts for dual-mode display
    if not cumulative_only and getattr(args, 'cumulative', False):
        import numpy as np
        cumulative = np.cumsum(np.asarray(counts, dtype=int)).tolist()
    else:
        cumulative = None

    # Determine column layout from terminal width
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    label_width = min(_MAX_LABEL_WIDTH, max(len(lbl) for lbl in labels))

    # layout: "<label> | <bar> <count>" or
    #         "<label> | <bar> <count> | <cumulative>"
    count_digits = len(str(max_count))
    cumulative_label_width = len(str(cumulative[-1])) + 3 if cumulative else 0

    bar_area = (
        term_width
        - label_width
        - 3  # " | "
        - 1  # space before count
        - count_digits
        - cumulative_label_width
    )
    bar_area = max(bar_area, _MIN_BAR_COLS)

    console = Console(highlight=False)
    console.print()
    console.print(
        f'[bold]Event count per time bin[/bold] '
        f'[dim](bin size: {bin_size_label})[/dim]  '
        f'([dim]{len(events)} events total[/dim])'
    )
    console.print()

    for i, ((bin_start, bin_end, count), label) in enumerate(
        zip(bins, labels)
    ):
        # Scale bar length
        bar_len = (
            max(
                _MIN_BAR_COLS if count > 0 else 0,
                round(count / max_count * bar_area),
            )
            if max_count > 0 else 0
        )

        label_str = label.ljust(label_width)[:label_width]
        bar_str = _BAR_CHAR * bar_len
        count_str = str(count).rjust(count_digits)

        line = Text()
        line.append(label_str, style='cyan')
        line.append(' | ', style='dim')
        if bar_len > 0:
            line.append(bar_str, style='bright_blue')
        line.append(f' {count_str}', style='bold')

        if cumulative:
            cum_str = str(cumulative[i])
            line.append(' | ', style='dim')
            line.append(cum_str, style='bright_magenta')

        console.print(line)

    console.print()
    # Print scale legend
    scale_info = (
        f'Scale: full bar = {max_count} events  |  '
        f'one █ ≈ {max_count / bar_area:.1f} events'
        if bar_area > 0 and max_count > 0
        else ''
    )
    if scale_info:
        console.print(f'[dim]{scale_info}[/dim]')
    if cumulative:
        console.print(
            '[dim]Rightmost column shows cumulative event count[/dim]'
        )
    console.print()

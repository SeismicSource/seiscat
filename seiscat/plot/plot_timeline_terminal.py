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
    bin_events_by_time, bin_label, get_bin_size_label
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

    bins = bin_events_by_time(events, bins_spec)
    if not bins:
        err_exit('No events to plot.')
    bin_size_label = get_bin_size_label(bins, bins_spec)

    counts = [b[2] for b in bins]
    max_count = max(counts, default=1)
    labels = [bin_label(b[0], b[1]) for b in bins]

    # Determine column layout from terminal width
    term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    label_width = min(_MAX_LABEL_WIDTH, max(len(lbl) for lbl in labels))
    # layout: "<label> | <bar> <count>"
    #          label_width + 3 (` | `) + bar_cols + 1 + count_digits
    count_digits = len(str(max_count))
    bar_area = term_width - label_width - 3 - 1 - count_digits
    bar_area = max(bar_area, _MIN_BAR_COLS)

    console = Console(highlight=False)
    console.print()
    console.print(
        f'[bold]Event count per time bin[/bold] '
        f'[dim](bin size: {bin_size_label})[/dim]  '
        f'([dim]{len(events)} events total[/dim])'
    )
    console.print()

    for (bin_start, bin_end, count), label in zip(bins, labels):
        # Scale bar length
        if max_count > 0:
            bar_len = max(
                _MIN_BAR_COLS if count > 0 else 0,
                round(count / max_count * bar_area),
            )
        else:
            bar_len = 0

        label_str = label.ljust(label_width)[:label_width]
        bar_str = _BAR_CHAR * bar_len
        count_str = str(count).rjust(count_digits)

        line = Text()
        line.append(label_str, style='cyan')
        line.append(' | ', style='dim')
        if bar_len > 0:
            line.append(bar_str, style='bright_blue')
        line.append(f' {count_str}', style='bold')
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
    console.print()

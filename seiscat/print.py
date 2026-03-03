# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Printing functions for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
from contextlib import suppress
from .utils import err_exit
# Other modules are lazily imported inside functions to speed up startup time
# pylint: disable=import-outside-toplevel


def _print_catalog_stats(config):
    """
    Print catalog statistics.

    :param config: config object
    """
    from .database.dbfunctions import get_catalog_stats
    print(get_catalog_stats(config))


def _print_table_rows(header, body_rows):
    """
    Print table header and rows.

    :param header: header row string
    :param body_rows: list of body row strings
    """
    print(header)
    for row in body_rows:
        print(row)


def _print_catalog_table(config):
    """
    Pretty-print the catalog as a table.

    :param config: config object
    """
    from .database.dbfunctions import read_fields_and_rows_from_db
    # get fields and rows from database
    # rows are sorted by time and version and reversed if requested
    fields, rows = read_fields_and_rows_from_db(config)
    if len(rows) == 0:
        print('No events in catalog')
        return
    # Build plain text table
    max_len = [len(f) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            max_len[i] = max(max_len[i], len(str(val)))
    # Build header
    header = '  '.join(f'{f:{max_len[i]}}' for i, f in enumerate(fields))
    # Build body rows
    body_rows = []
    for row in rows:
        row_str = '  '.join(
            f'{("None" if val is None else str(val)):{max_len[i]}}'
            for i, val in enumerate(row)
        )
        body_rows.append(row_str)
    # Check if output is to a terminal
    if sys.stdout.isatty():
        # Use curses pager with fixed header for terminal output
        import curses
        try:
            curses.wrapper(_display_table_pager, header, body_rows)
        except (curses.error, OSError, KeyboardInterrupt):
            # Fallback to simple print if curses fails
            _print_table_rows(header, body_rows)
    else:
        # Plain text output for pipes/files
        _print_table_rows(header, body_rows)


def _pager_loop_iteration(stdscr, header, body_rows, pager_state):
    """
    Handle one iteration of the table pager loop.

    :param stdscr: curses window
    :param header: header row string
    :param body_rows: list of body row strings
    :param pager_state: dictionary with 'offset', 'selected_row',
        'h_scroll' state
    :return: True to continue, False to exit
    """
    import curses
    max_y, max_x = stdscr.getmaxyx()
    available_rows = max_y - 2  # -2 for header and help line
    # Calculate max row width for horizontal scrolling
    max_row_width = max(len(header), max(len(row) for row in body_rows))
    # Only enable horizontal scrolling if table is wider than terminal
    enable_h_scroll = max_row_width > max_x
    # Constrain horizontal scroll to valid range
    if enable_h_scroll:
        pager_state['h_scroll'] = max(
            0, min(pager_state['h_scroll'], max_row_width - max_x)
        )
    else:
        pager_state['h_scroll'] = 0
    stdscr.clear()
    # Display header in reverse video
    with suppress(curses.error):
        header_scroll = header[pager_state['h_scroll']:]
        header_display = (
            header_scroll[:max_x] if len(header_scroll) > max_x
            else header_scroll
        )
        stdscr.addstr(0, 0, header_display, curses.A_REVERSE)
    # Display visible body rows with alternating font colors
    for i, row in enumerate(
            body_rows[pager_state['offset']:
                      pager_state['offset'] + available_rows]
    ):
        with suppress(curses.error):
            row_scroll = row[pager_state['h_scroll']:]
            row_display = (
                row_scroll[:max_x] if len(row_scroll) > max_x
                else row_scroll
            )
            # Alternate colors based on row index in the entire dataset
            row_index = pager_state['offset'] + i

            # Check if this is the selected row
            if row_index == pager_state['selected_row']:
                # Highlight selected row with reverse video
                color_attr = curses.A_REVERSE
            else:
                    # Even rows: default color
                try:
                    color_attr = (
                        curses.color_pair(1)
                        if row_index % 2 == 0
                        else curses.color_pair(2)
                    )
                except curses.error:
                    color_attr = 0
            stdscr.addstr(1 + i, 0, row_display, color_attr)
    # Display help line at the bottom with status
    with suppress(curses.error):
        # Calculate visible event range
        first_visible = pager_state['offset'] + 1
        last_visible = min(
            pager_state['offset'] + available_rows, len(body_rows)
        )
        total_events = len(body_rows)

        # Left side: help text, Right side: event counter
        help_text = (
            'q/Esc: quit | j/↓/k/↑: move | h/←/l/→: scroll | '
            'Space/f: page↓ | b: page↑ | g: home | G: end'
        )
        status_text = (
            f'Events {first_visible}-{last_visible} of {total_events}'
        )

        # Create the full status bar
        available_space = max_x - len(status_text)
        full_text = (
            help_text
            + ' ' * (available_space - len(help_text))
            + status_text
            if available_space > len(help_text)
            else status_text.rjust(max_x)
        )
        help_display = full_text[:max_x]
        stdscr.addstr(max_y - 1, 0, help_display, curses.A_REVERSE)
    stdscr.refresh()

    # Handle input
    try:
        key = stdscr.getch()
    except (OSError, KeyboardInterrupt):
        return False
    if key in [ord('q'), 27]:  # q or Esc
        return False
    if enable_h_scroll and key in [curses.KEY_LEFT, ord('h')]:  # Scroll left
        pager_state['h_scroll'] = max(0, pager_state['h_scroll'] - 5)
    elif enable_h_scroll and key in [curses.KEY_RIGHT, ord('l')]:  # Scroll right
        pager_state['h_scroll'] = min(
            max_row_width - max_x, pager_state['h_scroll'] + 5
        )
    elif key in [curses.KEY_DOWN, ord('j')]:
        if pager_state['selected_row'] < len(body_rows) - 1:
            pager_state['selected_row'] += 1
            # Auto-scroll if selected row goes off screen
            if pager_state['selected_row'] >= (
                    pager_state['offset'] + available_rows):
                pager_state['offset'] += 1
    elif key in [curses.KEY_UP, ord('k')]:
        if pager_state['selected_row'] > 0:
            pager_state['selected_row'] -= 1
            # Auto-scroll if selected row goes off screen
            if pager_state['selected_row'] < pager_state['offset']:
                pager_state['offset'] -= 1
    elif key in [curses.KEY_PPAGE, ord('b')]:  # Page Up
        pager_state['offset'] = max(
            0, pager_state['offset'] - available_rows
        )
        pager_state['selected_row'] = max(
            0, pager_state['selected_row'] - available_rows
        )
    elif key in [curses.KEY_NPAGE, ord('f'), ord(' ')]:  # Page Down
        pager_state['offset'] = max(
            0,
            min(
                len(body_rows) - available_rows,
                pager_state['offset'] + available_rows
            )
        )
        pager_state['selected_row'] = min(
            len(body_rows) - 1,
            pager_state['selected_row'] + available_rows
        )
    elif key in [curses.KEY_HOME, ord('g')]:  # Home
        pager_state['offset'] = 0
        pager_state['selected_row'] = 0
    elif key in [curses.KEY_END, ord('G')]:  # End
        pager_state['selected_row'] = len(body_rows) - 1
        pager_state['offset'] = max(0, len(body_rows) - available_rows)
    return True


def _display_table_pager(stdscr, header, body_rows):
    """
    Display table with fixed header and alternating row font colors using
    curses scrolling.

    :param stdscr: curses window
    :param header: header row string
    :param body_rows: list of body row strings
    """
    import curses
    # Use terminal's default colors
    with suppress(curses.error, AttributeError):
        curses.use_default_colors()
    # Initialize color pairs for alternating rows
    # Color pair 1: normal row (default foreground)
    # Color pair 2: alternating row (cyan/blue foreground)
    if curses.has_colors():
        with suppress(curses.error):
            curses.init_pair(1, -1, -1)  # default fg/bg
            curses.init_pair(2, curses.COLOR_CYAN, -1)  # cyan fg, default bg
    stdscr.keypad(True)
    with suppress(curses.error, AttributeError):
        curses.curs_set(0)  # Hide cursor
    # Track pager state (offset, selected row, horizontal scroll)
    pager_state = {'offset': 0, 'selected_row': 0, 'h_scroll': 0}
    while True:
        should_continue = _pager_loop_iteration(
            stdscr, header, body_rows, pager_state
        )
        if not should_continue:
            break


def print_catalog(config):
    """
    Print catalog.

    :param config: config object
    """
    args = config['args']
    try:
        if args.format == 'stats':
            _print_catalog_stats(config)
        elif args.format == 'table':
            _print_catalog_table(config)
        else:
            err_exit(f'Unknown format "{args.format}"')
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

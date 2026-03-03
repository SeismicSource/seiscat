# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Interactive table pager using curses.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import curses
from contextlib import suppress


class PagerException(Exception):
    """Exception raised when the pager fails."""


def _handle_pager_input(
        stdscr, pager_state, body_rows, available_rows,
        enable_h_scroll, max_row_width, max_x):
    """
    Handle keyboard input for pager navigation.

    :param stdscr: curses window
    :param pager_state: dictionary with pager state
    :param body_rows: list of body row strings
    :param available_rows: number of rows available for display
    :param enable_h_scroll: whether horizontal scrolling is enabled
    :param max_row_width: maximum row width in characters
    :param max_x: terminal width
    :return: True to continue, False to exit
    """
    try:
        key = stdscr.getch()
    except (OSError, KeyboardInterrupt):
        return False
    if key in [ord('q'), 27]:  # q or Esc
        return False
    if enable_h_scroll and key in [curses.KEY_LEFT, ord('h')]:
        # Scroll left
        pager_state['h_scroll'] = max(0, pager_state['h_scroll'] - 5)
    elif enable_h_scroll and key in [curses.KEY_RIGHT, ord('l')]:
        # Scroll right
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
    # Use erase() instead of clear() to avoid flickering
    # erase() stages the clear for next refresh(),
    # while clear() blanks immediately
    stdscr.erase()
    # Suppress curses.error for all display operations to handle:
    # - Terminal resize race conditions (between getmaxyx() and addstr())
    # - Bottom-right corner quirks (some terminals error on last cell)
    # - Terminal capability differences across platforms
    # This ensures the pager remains functional even with partial display
    with suppress(curses.error):
        # Display header in reverse video
        header_scroll = header[pager_state['h_scroll']:]
        header_display = (
            header_scroll[:max_x] if len(header_scroll) > max_x
            else header_scroll
        )
        stdscr.addstr(0, 0, header_display, curses.A_REVERSE)
        # Display visible body rows with alternating font colors
        for i, row in enumerate(
            body_rows[
                pager_state['offset']:
                pager_state['offset'] + available_rows
            ]
        ):
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
                # Use alternating colors if color pairs were initialized
                # Fallback to no color if color pairs are unavailable
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
    return _handle_pager_input(
        stdscr, pager_state, body_rows, available_rows,
        enable_h_scroll, max_row_width, max_x
    )


def display_table_pager(header, body_rows):
    """
    Display table with fixed header and alternating row font colors using
    curses scrolling.

    :param header: header row string
    :param body_rows: list of body row strings
    :raises PagerException: if the pager fails to initialize or run
    """
    def _display_table_pager_wrapper(stdscr):
        """Wrapper for curses.wrapper."""
        # Use terminal's default colors (may not be supported on all terminals)
        with suppress(curses.error, AttributeError):
            curses.use_default_colors()
        # Initialize color pairs for alternating rows
        # Color pair 1: normal row (default foreground)
        # Color pair 2: alternating row (cyan/blue foreground)
        if curses.has_colors():
            # Suppress errors if color pair initialization fails
            with suppress(curses.error):
                # default fg/bg
                curses.init_pair(1, -1, -1)
                # cyan fg, default bg
                curses.init_pair(2, curses.COLOR_CYAN, -1)
        stdscr.keypad(True)
        # Hide cursor (not supported on all terminals)
        with suppress(curses.error, AttributeError):
            curses.curs_set(0)
        # Track pager state (offset, selected row, horizontal scroll)
        pager_state = {'offset': 0, 'selected_row': 0, 'h_scroll': 0}
        while True:
            should_continue = _pager_loop_iteration(
                stdscr, header, body_rows, pager_state
            )
            if not should_continue:
                break

    try:
        curses.wrapper(_display_table_pager_wrapper)
    except (curses.error, OSError, KeyboardInterrupt) as e:
        raise PagerException(f"Pager failed: {e}") from e

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


def _copy_to_clipboard(text):
    """
    Copy text to system clipboard (cross-platform).

    :param text: text to copy to clipboard
    :return: True if successful, False otherwise
    """
    # Lazy import to avoid slowdown at module load time
    # pylint: disable=import-outside-toplevel
    import platform
    import subprocess
    system = platform.system()
    try:
        if system == 'Darwin':  # macOS
            subprocess.run(
                ['pbcopy'],
                input=text.encode('utf-8'),
                check=True
            )
        elif system == 'Windows':
            subprocess.run(
                ['clip'],
                input=text.encode('utf-16le'),
                check=True
            )
        else:  # Linux and other Unix-like systems
            # Try xclip first, then xsel
            try:
                subprocess.run(
                    ['xclip', '-selection', 'clipboard'],
                    input=text.encode('utf-8'),
                    check=True
                )
            except FileNotFoundError:
                subprocess.run(
                    ['xsel', '--clipboard', '--input'],
                    input=text.encode('utf-8'),
                    check=True
                )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _format_rows(fields, rows):
    """
    Format raw data into aligned string rows.

    :param fields: list of column names
    :param rows: list of row data (each row is a list/tuple)
    :return: tuple of (header_string, body_rows_list)
    """
    max_len = [len(f) for f in fields]
    for row in rows:
        for i, val in enumerate(row):
            if i < len(max_len):
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
    return header, body_rows


def _display_message_popup(stdscr, message):
    """
    Display a message popup and wait for any keypress.

    :param stdscr: curses window
    :param message: message to display
    """
    max_y, max_x = stdscr.getmaxyx()
    # Calculate popup dimensions based on message length
    message_len = len(message)
    popup_width = min(message_len + 6, max_x - 4)
    popup_height = 5  # Simple popup with just the message
    popup_y = (max_y - popup_height) // 2
    popup_x = (max_x - popup_width) // 2
    
    try:
        # Clear popup area with spaces to remove background text
        for y in range(popup_y, popup_y + popup_height):
            stdscr.addstr(y, popup_x, ' ' * popup_width)
        # Draw top border
        top_border = '╔' + '═' * (popup_width - 2) + '╗'
        stdscr.addstr(popup_y, popup_x, top_border, curses.A_BOLD)
        # Draw message centered
        message_padding = popup_width - 2 - len(message)
        message_left = message_padding // 2
        message_right = message_padding - message_left
        message_line = (
            '║' + ' ' * message_left + message +
            ' ' * message_right + '║'
        )
        stdscr.addstr(popup_y + 1, popup_x, message_line, curses.A_BOLD)
        # Draw blank line
        blank_line = '║' + ' ' * (popup_width - 2) + '║'
        stdscr.addstr(popup_y + 2, popup_x, blank_line)
        # Draw instruction
        instruction = 'Press any key'
        inst_padding = popup_width - 2 - len(instruction)
        inst_left = inst_padding // 2
        inst_right = inst_padding - inst_left
        inst_line = (
            '║' + ' ' * inst_left + instruction +
            ' ' * inst_right + '║'
        )
        stdscr.addstr(popup_y + 3, popup_x, inst_line)
        # Draw bottom border
        bottom_border = '╚' + '═' * (popup_width - 2) + '╝'
        stdscr.addstr(popup_y + 4, popup_x, bottom_border, curses.A_BOLD)
        stdscr.refresh()
        # Wait for any keypress
        stdscr.getch()
    except curses.error:
        pass


def _draw_sort_popup_and_get_input(
        stdscr, popup_y, popup_x, popup_width, popup_height,
        fields, selected_idx):
    """
    Draw sort selector popup and handle user input.

    :param stdscr: curses window
    :param popup_y: popup top position
    :param popup_x: popup left position
    :param popup_width: popup width
    :param popup_height: popup height
    :param fields: list of field names
    :param selected_idx: currently selected field index
    :return: tuple (selected_col, new_selected_idx) where selected_col
        is the column to select (or None to continue), and new_selected_idx
        is the updated selection index for next iteration
    """
    try:
        # Clear popup area with spaces to remove background text
        for y in range(popup_y, popup_y + popup_height):
            stdscr.addstr(y, popup_x, ' ' * popup_width)
        # Draw top border
        top_border = '╔' + '═' * (popup_width - 2) + '╗'
        stdscr.addstr(popup_y, popup_x, top_border, curses.A_BOLD)
        # Draw title
        title = ' Sort by column '
        title_padding = popup_width - 2 - len(title)
        title_left = title_padding // 2
        title_right = title_padding - title_left
        title_line = (
            '║' + ' ' * title_left + title +
            ' ' * title_right + '║'
        )
        stdscr.addstr(popup_y + 1, popup_x, title_line, curses.A_BOLD)
        # Draw separator
        sep_line = '╠' + '═' * (popup_width - 2) + '╣'
        stdscr.addstr(popup_y + 2, popup_x, sep_line, curses.A_BOLD)
        # Draw field options
        display_rows = popup_height - 4
        start_idx = max(0, selected_idx - display_rows // 2)
        end_idx = min(len(fields), start_idx + display_rows)
        for i in range(display_rows):
            y = popup_y + 3 + i
            if start_idx + i < end_idx:
                field_idx = start_idx + i
                field_name = fields[field_idx]
                prefix = f'{field_idx + 1}. ' if field_idx < 9 else '  '
                content = f'{prefix}{field_name}'
            else:
                content = ''
            # Pad or truncate to fit width (accounting for borders)
            padding = ' ' * (popup_width - 4)
            content = (content + padding)[:popup_width - 4]
            is_selected = (
                start_idx + i < len(fields) and
                start_idx + i == selected_idx
            )
            option_line = f'║ {content} ║'
            if is_selected:
                stdscr.addstr(
                    y, popup_x, option_line, curses.A_REVERSE)
            else:
                stdscr.addstr(y, popup_x, option_line)
        # Draw bottom border
        bottom_border = '╚' + '═' * (popup_width - 2) + '╝'
        bottom_y = popup_y + popup_height - 1
        stdscr.addstr(bottom_y, popup_x, bottom_border,
                     curses.A_BOLD)
        stdscr.refresh()
        # Handle input
        key = stdscr.getch()
        if key in [ord('q'), 27]:  # q or Esc
            return (None, selected_idx)
        if key in [ord('\n'), ord(' ')]:  # Enter or Space
            return (selected_idx, selected_idx)
        elif key in [curses.KEY_DOWN, ord('j')]:
            selected_idx = min(len(fields) - 1, selected_idx + 1)
            return (None, selected_idx)
        elif key in [curses.KEY_UP, ord('k')]:
            selected_idx = max(0, selected_idx - 1)
            return (None, selected_idx)
        elif chr(key).isdigit():
            col_num = int(chr(key)) - 1
            if 0 <= col_num < len(fields):
                return (col_num, selected_idx)
            return (None, selected_idx)
        return (None, selected_idx)
    except curses.error:
        return (None, selected_idx)


def _display_sort_selector(stdscr, raw_data):

    """
    Display an interactive sort field selector popup.

    :param stdscr: curses window
    :param raw_data: dict with 'fields' list
    :return: selected column index (0-indexed) or None if cancelled
    """
    max_y, max_x = stdscr.getmaxyx()
    fields = raw_data['fields']
    # Calculate popup dimensions
    max_field_len = max(len(f) for f in fields) if fields else 0
    title_len = len(' Sort by column ')
    # Ensure popup is wide enough for both title and fields
    min_width = max(max_field_len + 6, title_len + 4)
    popup_width = min(min_width, max_x - 4)
    popup_height = min(len(fields) + 4, max_y - 4)
    popup_y = (max_y - popup_height) // 2
    popup_x = (max_x - popup_width) // 2
    selected_idx = 0
    while True:
        selected_col, selected_idx = _draw_sort_popup_and_get_input(
            stdscr, popup_y, popup_x, popup_width, popup_height,
            fields, selected_idx
        )
        if selected_col is not None:
            return selected_col


def _handle_pager_input(
        stdscr, pager_state, body_rows, available_rows,
        enable_h_scroll, max_row_width, max_x, raw_data=None):
    """
    Handle keyboard input for pager navigation and sorting.

    :param stdscr: curses window
    :param pager_state: dictionary with pager state
    :param body_rows: list of body row strings
    :param available_rows: number of rows available for display
    :param enable_h_scroll: whether horizontal scrolling is enabled
    :param max_row_width: maximum row width in characters
    :param max_x: terminal width
    :param raw_data: optional dict with fields and rows for sorting
    :return: True to continue, False to exit
    """
    try:
        key = stdscr.getch()
    except (OSError, KeyboardInterrupt):
        return False
    if key in [ord('q'), 27]:  # q or Esc
        return False
    # Handle copy event ID with 'c' key
    if raw_data and key == ord('c'):
        selected_row_idx = pager_state['selected_row']
        if 0 <= selected_row_idx < len(raw_data['rows']):
            if row := raw_data['rows'][selected_row_idx]:
                # Copy first column (event ID) to clipboard
                event_id = str(row[0])
                if _copy_to_clipboard(event_id):
                    message = f'evid {event_id} copied to clipboard'
                else:
                    message = 'Clipboard copy failed'
                _display_message_popup(stdscr, message)
        return True
    # Handle sort field selector with 's' key
    if raw_data and key == ord('0'):
        # Revert to default sort order
        pager_state['sort_col'] = pager_state.get(
            'default_sort_col'
        )
        pager_state['sort_asc'] = pager_state.get(
            'default_sort_asc', True
        )
        # Re-sort the data
        if pager_state['sort_col'] is not None:
            with suppress(IndexError, TypeError):
                _sort_rows_by_column(
                    pager_state['sort_col'], raw_data, pager_state
                )
        return True
    # Handle sort field selector with 's' key
    if raw_data and key == ord('s'):
        selected_col = _display_sort_selector(stdscr, raw_data)
        if selected_col is not None:
            # Check if sorting the same column (toggle sort direction)
            if pager_state.get('sort_col') == selected_col:
                pager_state['sort_asc'] = not pager_state.get(
                    'sort_asc', True
                )
            else:
                pager_state['sort_col'] = selected_col
                pager_state['sort_asc'] = True
            # Sort the raw data
            with suppress(IndexError, TypeError):
                _sort_rows_by_column(selected_col, raw_data, pager_state)
        return True
    # Handle column sorting with number keys (1-9)
    if raw_data and chr(key) in '123456789':
        col_num = int(chr(key)) - 1  # Convert to 0-indexed
        if col_num < len(raw_data['fields']):
            # Check if sorting the same column (toggle sort direction)
            if pager_state.get('sort_col') == col_num:
                pager_state['sort_asc'] = not pager_state.get(
                    'sort_asc', True
                )
            else:
                pager_state['sort_col'] = col_num
                pager_state['sort_asc'] = True
            # Sort the raw data
            with suppress(IndexError, TypeError):
                _sort_rows_by_column(col_num, raw_data, pager_state)
    elif key in [curses.KEY_LEFT, ord('h')]:
        if enable_h_scroll:
            # Scroll left
            pager_state['h_scroll'] = max(0, pager_state['h_scroll'] - 5)
    elif key in [curses.KEY_RIGHT, ord('l')]:
        if enable_h_scroll:
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


def _sort_rows_by_column(col_index, raw_data, pager_state):
    """
    Sort rows by the specified column index.

    :param col_index: column index to sort by
    :param raw_data: dict with 'rows' list to sort
    :param pager_state: dict to update offset and selected_row
    """
    raw_data['rows'].sort(
        key=lambda row: (
            row[col_index] if col_index < len(row) else ''
        ),
        reverse=not pager_state['sort_asc']
    )
    # Reset offset and selected row after sorting
    pager_state['offset'] = 0
    pager_state['selected_row'] = 0


def _pager_loop_iteration(
        stdscr, header, body_rows, pager_state, raw_data=None):
    """
    Handle one iteration of the table pager loop.

    :param stdscr: curses window
    :param header: header row string
    :param body_rows: list of body row strings
    :param pager_state: dictionary with 'offset', 'selected_row',
        'h_scroll', 'sort_col', 'sort_asc' state
    :param raw_data: optional dict with fields and rows for sorting
    :return: True to continue, False to exit
    """
    max_y, max_x = stdscr.getmaxyx()
    # Determine how many help lines we'll need
    # Build help text components (will be reused below)
    help_line1 = 'q/Esc: quit | j/↓/k/↑: move | h/←/l/→: scroll | c: copy evid'
    help_line2 = (
        'Space/f: page↓ | b: page↑ | g: home | G: end | '
        '0: dflt | 1-9: sort | s: sort'
    )
    # Build status text (needed to determine help layout)
    first_visible = 1  # Will recalculate below when needed
    total_events = len(body_rows)
    sort_info = ''
    if raw_data and pager_state.get('sort_col') is not None:
        sort_col = pager_state['sort_col']
        if sort_col < len(raw_data['fields']):
            field_name = raw_data['fields'][sort_col]
        else:
            field_name = f'Col{sort_col + 1}'
        sort_dir = '↑' if pager_state.get('sort_asc', True) else '↓'
        sort_info = f' | Sorted by {field_name} {sort_dir}'
    # Placeholder status text
    status_text = f'Events 1-{total_events} of {total_events}{sort_info}'
    # Determine number of help lines needed
    full_help = f'{help_line1} | {help_line2}'
    full_line = f'{full_help} | {status_text}'
    num_help_lines = 1
    if len(full_line) > max_x and max_y > 3:
        num_help_lines = 2
    # -1 for header, -num_help_lines for help lines
    available_rows = max_y - 1 - num_help_lines
    # Re-format rows if sorting has changed
    if raw_data and pager_state.get('sort_col') is not None:
        header, body_rows = _format_rows(
            raw_data['fields'], raw_data['rows']
        )
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
    # Suppress curses.error for content display to handle:
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
    # Display help lines at the bottom (outside suppress block)
    # Recalculate visible event range with actual available_rows
    first_visible = pager_state['offset'] + 1
    last_visible = min(
        pager_state['offset'] + available_rows, len(body_rows)
    )
    # Build updated status text
    status_text = (
        f'Events {first_visible}-{last_visible} of '
        f'{total_events}{sort_info}'
    )
    with suppress(curses.error):
        if num_help_lines == 1:
            # Everything fits on one line (or not enough space)
            full_help = f'{help_line1} | {help_line2}'
            full_line = f'{full_help} | {status_text}'
            if len(full_line) <= max_x:
                help_display = (full_line + ' ' * max_x)[:max_x]
            else:
                # Truncate or show status only
                help_display = (status_text + ' ' * max_x)[:max_x]
            stdscr.addstr(max_y - 1, 0, help_display, curses.A_REVERSE)
        else:
            # Use two lines
            # Line 1: First part of help + status
            width_available = (
                max_x - len(help_line1) - len(status_text) - 3
            )
            padding_width = max(0, width_available)
            line1 = f'{help_line1} | ' + ' ' * padding_width + status_text
            line1 = (line1 + ' ' * max_x)[:max_x]
            # Line 2: Second part of help
            line2 = (help_line2 + ' ' * max_x)[:max_x]
            stdscr.addstr(max_y - 2, 0, line1, curses.A_REVERSE)
            stdscr.addstr(max_y - 1, 0, line2, curses.A_REVERSE)
    stdscr.refresh()
    # Handle input
    return _handle_pager_input(
        stdscr, pager_state, body_rows, available_rows,
        enable_h_scroll, max_row_width, max_x, raw_data=raw_data
    )


def display_table_pager(
        header, body_rows, raw_data=None,
        default_sort_col=None, default_sort_asc=True):
    """
    Display table with fixed header and alternating row font colors using
    curses scrolling. Supports interactive sorting by column.

    :param header: header row string
    :param body_rows: list of body row strings
    :param raw_data: optional dict with 'fields' (list of column names) and
        'rows' (list of row data lists) for interactive sorting
    :param default_sort_col: default column index for sorting (can be
        restored with 0 key)
    :param default_sort_asc: default sort direction (True for ascending)
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
        # Disable mouse events to prevent buffer overflow
        with suppress(curses.error, AttributeError):
            curses.mousemask(0)
        # Hide cursor (not supported on all terminals)
        with suppress(curses.error, AttributeError):
            curses.curs_set(0)
        # Track pager state (offset, selected row, horizontal scroll, sorting)
        pager_state = {
            'offset': 0,
            'selected_row': 0,
            'h_scroll': 0,
            'sort_col': default_sort_col,
            'sort_asc': default_sort_asc,
            'default_sort_col': default_sort_col,
            'default_sort_asc': default_sort_asc
        }
        while True:
            should_continue = _pager_loop_iteration(
                stdscr, header, body_rows, pager_state, raw_data=raw_data
            )
            if not should_continue:
                break

    try:
        curses.wrapper(_display_table_pager_wrapper)
    except (curses.error, OSError, KeyboardInterrupt) as e:
        raise PagerException(f"Pager failed: {e}") from e

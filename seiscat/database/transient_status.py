# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Transient terminal status helpers.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
from contextlib import contextmanager


def _can_show_transient_status():
    """Return True when transient status can be shown safely."""
    return sys.stdout.isatty() and sys.stderr.isatty()


@contextmanager
def transient_status(initial_message):
    """
    Show a transient status line on stderr and clear it on exit.

    Yields an update callable to change the message while active.
    """
    if not _can_show_transient_status():
        yield lambda _message: None
        return

    width = len(initial_message)

    def _update(message):
        nonlocal width
        # Clear previous line if the new message is shorter.
        sys.stderr.write(f'\r{" " * width}\r{message}')
        sys.stderr.flush()
        width = max(width, len(message))

    _update(initial_message)
    try:
        yield _update
    finally:
        sys.stderr.write(f'\r{" " * width}\r')
        sys.stderr.flush()

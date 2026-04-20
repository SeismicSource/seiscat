# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Logo printing helpers for `seiscat self logo`."""
import shutil
import sys

from ..utils.logo import SEISCAT_LOGO, SEISCAT_LOGO_SMALL


def _logo_width(logo):
    """Return the maximum line width of a multi-line logo string."""
    return max(len(line) for line in logo.splitlines())


def print_logo_small():
    """Print the compact seiscat logo."""
    maxwidth = _logo_width(SEISCAT_LOGO_SMALL)
    columns, _ = shutil.get_terminal_size()
    if columns < maxwidth:
        print('Terminal too narrow to display the compact seiscat logo 🐱.')
        sys.exit(0)
    print(SEISCAT_LOGO_SMALL)


def print_logo(compact=False):
    """Print the beautiful ascii-art seiscat logo."""
    if compact:
        print_logo_small()
        return

    maxwidth = _logo_width(SEISCAT_LOGO)
    columns, _ = shutil.get_terminal_size()
    if columns < maxwidth:
        print('Terminal too narrow: showing compact seiscat logo 🐱.')
        print_logo_small()
        return
    print(SEISCAT_LOGO)

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Utility functions for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .exit import err_exit, ExceptionExit, set_debug  # noqa
from .conversion import float_or_none, int_or_none  # noqa
from .sample_script import write_sample_script  # noqa
from .print_logo import print_logo  # noqa
from .write_ok import write_ok  # noqa

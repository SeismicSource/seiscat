# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Exit functions.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
import contextlib
import traceback
DEBUG = False


def set_debug(debug):
    """Enable or disable debug mode for error handling."""
    # pylint: disable=global-statement
    global DEBUG
    DEBUG = bool(debug)


def err_exit(msg):
    """
    Print an error message and exit.

    :param msg: error message
    """
    msg = str(msg)
    sys.stderr.write(msg + '\n')
    sys.exit(1)


class ExceptionExit(contextlib.AbstractContextManager):
    """
    Context manager to exit when an exception is raised.
    """

    def __init__(self, additional_msg=None):
        """
        Initialize the context manager.

        :param additional_msg: additional message to print
        """
        self.additional_msg = additional_msg

    def __exit__(self, exc_type, exc_value, _traceback):
        if exc_type:
            if DEBUG:
                traceback.print_exception(exc_type, exc_value, _traceback)
            if self.additional_msg is not None:
                msg = f'{self.additional_msg}: {exc_value}'
            else:
                msg = exc_value
            err_exit(msg)

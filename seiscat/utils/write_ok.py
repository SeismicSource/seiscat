# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Check if it is ok to write to a file.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os


def write_ok(filepath):
    """
    Check if it is ok to write to a file.

    :param filepath: path to the file
    :returns: True if it is ok to write to the file, False otherwise
    """
    if os.path.exists(filepath):
        ans = input(
            f'"{filepath}" already exists. Do you want to overwrite it? [y/N] '
        )
        return ans in ['y', 'Y']
    return True

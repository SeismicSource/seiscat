# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Seiscat

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
import shutil

# flake8: noqa
SEISCAT_LOGO = r"""

                         ██████                                     ██████
                        ██   ██████                             ██████  ███
                       ██         █████   ███████████████    ████        ███
                      ███  ████      █████████  ███  █████████      ████  ███
                      ██  ████████        ████  ███  ████        ████████  ██
                     ███  ██████          ████  ███  ████          ██████  ██
                     ███  ████             ██   ███   ██             ████  ███
                     ███  ██                █    █    █                ██  ███
                     ███        ███████                     ███████        ███
                     ███                                                   ███
                     ███      ███████████                  ██████████      ███
                     ██     ███   ███   ██               ██   ████   ██     ██
                    ███    ██  ██    ███ ███            ██  ██    █   ██    ███
                    ███   ██  █  ████  █  ██           ██  █  ████  █  ██   ███
                    ███   ██  █ ██   █  █ ██           ██ ██ █   ██ █  ██   ███
                    ███   ██  █  █████ ██ ██           ██  █ ██████ █  ██   ███
               ████  ██    ██ ███     ██ ██             ██ ██      ██ ██    ███ █████
              ██ ███████ ██ ███  ████   ██     █████     ██   ████   ██ ██ ███████ ███
             ███    ███████   ██████████        ███        ██████████    ██████     ██
   ████      ██        ██                 ██    ███    ██                 ███       ███      ███
     █████ ████    ███  █████              ██████ ██████              █████  ████    ███ █████
        █████     ██████████                                           ███████ ██     █████
                   ██     ████                                       ████     ███
                   ██        ████                                 ████        ███
                  ██           █████                           █████           ███
             ██████                ██████                ███████                ██████
             ██                        ████████████████████                         ██

                           ████████                    █████
                          ███        █████ ██ ██████  ██       ██ ██████
                           ███████   ███   ██ ███    ██       ██ █  ██
                                ███ ██    ██    ███ ██   ██ ██████ ██
                           ███████  █████ ██ ██████  █████ ██    █ ██

"""


def print_logo():
    """
    Print the beautiful ascii-art seiscat logo.
    """
    maxwidth = max(len(line) for line in SEISCAT_LOGO.splitlines())
    columns, _ = shutil.get_terminal_size()
    if columns < maxwidth:
        print('Terminal too narrow to display the seiscat logo 🐱.')
        sys.exit(0)
    print(SEISCAT_LOGO)

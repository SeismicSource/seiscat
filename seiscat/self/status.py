# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Status command for seiscat self."""
from __future__ import annotations

import os
import sys
from importlib.util import find_spec

from .completion import completion_status
from .install_detection import detect_install_context
from .update import get_latest_release_version, _parse_version
from ..utils.logo import SEISCAT_LOGO_SMALL_NO_TXT


OPTIONAL_PLOTTING_MODULES = ('cartopy', 'plotly', 'pandas', 'folium')

_ANSI_RESET = '\033[0m'
# Match rich_argparse defaults used in parser output:
# argparse.groups=dark_orange, argparse.metavar=dark_cyan
_ANSI_BOLD = '\033[1m'
_ANSI_DARK_ORANGE = '\033[38;5;208m'
_ANSI_DARK_CYAN = '\033[36m'
_ANSI_GREEN = '\033[32m'
_ANSI_YELLOW = '\033[33m'
_ANSI_RED = '\033[31m'


def _use_color():
    return sys.stdout.isatty() and os.getenv('NO_COLOR') is None


def _colorize(text, color_code, enabled):
    return f'{color_code}{text}{_ANSI_RESET}' if enabled else text


def _key_label(label, color_enabled):
    return _colorize(label, _ANSI_DARK_CYAN, color_enabled)


def _status_label(installed, color_enabled):
    if installed:
        mark = _colorize('✓', _ANSI_GREEN, color_enabled)
        return f"{mark}{_colorize('installed', _ANSI_GREEN, color_enabled)}"
    mark = _colorize('✗', _ANSI_RED, color_enabled)
    return f"{mark}{_colorize('missing', _ANSI_RED, color_enabled)}"


def _update_label(update_state, color_enabled):
    if update_state == 'up to date':
        mark = _colorize('✓', _ANSI_GREEN, color_enabled)
        return f"{mark}{_colorize(update_state, _ANSI_GREEN, color_enabled)}"
    if update_state == 'update available':
        mark = _colorize('!', _ANSI_YELLOW, color_enabled)
        return f"{mark} {_colorize(update_state, _ANSI_YELLOW, color_enabled)}"
    return _colorize(update_state, _ANSI_CYAN, color_enabled)


def _update_state(context, latest_release):
    if not latest_release or context.version_installed == 'unknown':
        return 'unknown'
    installed = _parse_version(context.version_installed)
    latest = _parse_version(latest_release)
    return 'update available' if installed < latest else 'up to date'


def _optional_plotting_status():
    return {
        module: find_spec(module) is not None
        for module in OPTIONAL_PLOTTING_MODULES
    }


def get_self_status():
    """Return status dictionary for seiscat self status output."""
    context = detect_install_context()
    latest_release = get_latest_release_version()
    comp = completion_status()
    return {
        'installed_version': context.version_installed,
        'installer': context.installer,
        'channel': context.channel,
        'latest_release': latest_release or 'unknown',
        'update_state': _update_state(context, latest_release),
        'optional_plotting_modules': _optional_plotting_status(),
        'completion_installed': comp['installed'],
        'completion_shell': comp['shell'],
        'completion_details': comp['details'],
    }


def print_self_status():
    """Print status report for seiscat self status command."""
    status = get_self_status()
    color_enabled = _use_color()
    title = 'SeisCat self status'
    if color_enabled:
        title = _colorize(title, _ANSI_BOLD + _ANSI_DARK_ORANGE, True)
    print(SEISCAT_LOGO_SMALL_NO_TXT, end='')
    print(title)
    print('-------------------')
    print(
        f"{_key_label('Installed version:', color_enabled)} "
        f"{status['installed_version']}"
    )
    print(f"{_key_label('Installer:', color_enabled)} {status['installer']}")
    print(f"{_key_label('Channel:', color_enabled)} {status['channel']}")
    print(
        f"{_key_label('Latest release:', color_enabled)} "
        f"{status['latest_release']}"
    )
    print(
        f"{_key_label('Update status:', color_enabled)} "
        f"{_update_label(status['update_state'], color_enabled)}"
    )
    optional = status['optional_plotting_modules']
    optional_text = ', '.join(
        f'{name}= {_status_label(installed, color_enabled)}'
        for name, installed in optional.items()
    )
    print(
        f"{_key_label('Optional plotting modules:', color_enabled)} "
        f"{optional_text}"
    )
    print(
        f"{_key_label('Completion:', color_enabled)} "
        f"{_status_label(status['completion_installed'], color_enabled)} "
        f"({status['completion_shell']}: {status['completion_details']})"
    )

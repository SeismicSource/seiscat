# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Status command for seiscat self."""
from __future__ import annotations

from importlib.util import find_spec

from .completion import completion_status
from .install_detection import detect_install_context
from .update import get_latest_release_version, _parse_version


OPTIONAL_PLOTTING_MODULES = ('cartopy', 'plotly', 'pandas', 'folium')


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
    print('SeisCat self status')
    print('-------------------')
    print(f"Installed version: {status['installed_version']}")
    print(f"Installer: {status['installer']}")
    print(f"Channel: {status['channel']}")
    print(f"Latest release: {status['latest_release']}")
    print(f"Update status: {status['update_state']}")
    optional = status['optional_plotting_modules']
    optional_text = ', '.join(
        f"{name}={'installed' if installed else 'missing'}"
        for name, installed in optional.items()
    )
    print(f'Optional plotting modules: {optional_text}')
    print(
        'Completion: '
        f"{'installed' if status['completion_installed'] else 'missing'} "
        f"({status['completion_shell']}: {status['completion_details']})"
    )

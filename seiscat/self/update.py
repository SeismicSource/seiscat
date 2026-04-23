# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Update logic for seiscat self commands."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.request import urlopen

from .install_detection import detect_install_context

SEISCAT_GIT_URL = 'git+https://github.com/SeismicSource/seiscat.git'
SEISCAT_EXTRAS = ('cartopy', 'plotly', 'folium')


def _git_install_spec_with_extras():
    extras = ','.join(SEISCAT_EXTRAS)
    return f'seiscat[{extras}] @ {SEISCAT_GIT_URL}'


def _release_install_spec_with_extras():
    extras = ','.join(SEISCAT_EXTRAS)
    return f'seiscat[{extras}]'


def _manual_uv_command_message(package_spec):
    return (
        'Run this command manually in a fresh terminal:\n'
        f'  uv tool install "{package_spec}" --upgrade --force'
    )


def _parse_version(value):
    try:
        from packaging.version import Version
        return Version(value)
    except ImportError:
        from pkg_resources import parse_version
        return parse_version(value)


def get_latest_release_version(timeout=5):
    """Return latest release version from PyPI, or None on failure."""
    try:
        with urlopen(
            'https://pypi.org/pypi/seiscat/json',
            timeout=timeout
        ) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        return data['info']['version']
    except Exception:
        return None


def _run_checked(command):
    subprocess.run(command, check=True)


def _schedule_windows_pip_uninstall():
    """Schedule pip uninstall after current process exits (Windows only)."""
    helper_code = (
        'import ctypes, subprocess, sys, time; '
        'pid = int(sys.argv[1]); '
        'sync = 0x00100000; '
        'infinite = 0xFFFFFFFF; '
        'kernel32 = ctypes.windll.kernel32; '
        'handle = kernel32.OpenProcess(sync, False, pid); '
        'kernel32.WaitForSingleObject(handle, infinite) if handle else '
        'time.sleep(1); '
        'kernel32.CloseHandle(handle) if handle else None; '
        'subprocess.run([sys.executable, "-m", "pip", "uninstall", '
        '"-y", "seiscat"], check=False)'
    )
    subprocess.Popen([
        sys.executable,
        '-c',
        helper_code,
        str(os.getpid())
    ])


def _pip_update_release():
    _run_checked([
        sys.executable, '-m', 'pip', 'install', '--upgrade', 'seiscat'
    ])


def _uv_update_release():
    spec = _release_install_spec_with_extras()
    _run_checked(['uv', 'tool', 'install', spec, '--upgrade', '--force'])


def _pip_update_git():
    git_spec = _git_install_spec_with_extras()
    _run_checked([
        sys.executable, '-m', 'pip', 'install', '--upgrade', git_spec
    ])


def _uv_update_git():
    git_spec = _git_install_spec_with_extras()
    _run_checked([
        'uv', 'tool', 'install', git_spec, '--upgrade', '--force'
    ])


def _is_release_higher(installed_version, latest_release_version):
    return (
        _parse_version(latest_release_version)
        > _parse_version(installed_version)
    )


def update_seiscat(git=False):
    """Update SeisCat using release or git policy.

    Returns a user-facing status string.
    """
    context = detect_install_context()
    latest_release = get_latest_release_version()
    uv_available = shutil.which('uv') is not None

    if context.channel == 'editable':
        return 'Editable install detected: automatic update is disabled.'

    if git:
        if context.installer == 'uv' and uv_available:
            if os.name == 'nt':
                return (
                    'Windows detected: automatic uv self-update is disabled.\n'
                    + _manual_uv_command_message(
                        _git_install_spec_with_extras()
                    )
                )
            _uv_update_git()
            return 'Updated to latest git version using uv.'
        _pip_update_git()
        return 'Updated to latest git version using pip.'

    # Release-track behavior
    if context.channel == 'git' and latest_release:
        if _is_release_higher(context.version_installed, latest_release):
            # Switch back to release because release is newer
            if context.installer == 'uv' and uv_available:
                if os.name == 'nt':
                    return (
                        f'Latest release ({latest_release}) '
                        'is newer than installed git '
                        f'version ({context.version_installed}).\n'
                        'Windows detected: automatic uv self-update '
                        'is disabled.\n'
                        + _manual_uv_command_message(
                            _release_install_spec_with_extras()
                        )
                    )
                _uv_update_release()
                return (
                    f'Latest release ({latest_release}) '
                    'is newer than installed git '
                    f'version ({context.version_installed}); '
                    'switched to release via uv.'
                )
            _pip_update_release()
            return (
                f'Latest release ({latest_release}) '
                'is newer than installed git '
                f'version ({context.version_installed}); '
                'switched to release via pip.'
            )
        return (
            f'Installed git version ({context.version_installed}) '
            'is newer or equal '
            f'to latest release ({latest_release}). '
            'Use --git to keep git track explicitly.'
        )

    if (
        context.channel == 'release'
        and latest_release
        and context.version_installed != 'unknown'
        and not _is_release_higher(context.version_installed, latest_release)
    ):
        return (
            f'Installed release version ({context.version_installed}) '
            'is already up to date or newer '
            f'than latest release ({latest_release}).'
        )

    if context.installer == 'uv' and uv_available:
        if os.name == 'nt':
            return (
                'Windows detected: automatic uv self-update is disabled.\n'
                + _manual_uv_command_message(
                    _release_install_spec_with_extras()
                )
            )
        _uv_update_release()
        return 'Updated to latest release using uv.'
    _pip_update_release()
    return 'Updated to latest release using pip.'


def uninstall_seiscat(yes=False):
    """Uninstall SeisCat from current environment/tool backend."""
    from .completion import uninstall_completion

    if not yes:
        reply = input(
            'This will uninstall seiscat from this environment. '
            'Continue? [y/N]: '
        )
        if reply.strip().lower() not in {'y', 'yes'}:
            return 'Uninstall cancelled.'

    context = detect_install_context()
    uv_available = shutil.which('uv') is not None
    deferred_pip_uninstall = False
    try:
        if context.installer == 'uv' and uv_available:
            _run_checked(['uv', 'tool', 'uninstall', 'seiscat'])
            backend = 'uv'
        elif os.name == 'nt':
            _schedule_windows_pip_uninstall()
            backend = 'pip'
            deferred_pip_uninstall = True
        else:
            _run_checked([
                sys.executable, '-m', 'pip', 'uninstall', '-y', 'seiscat'
            ])
            backend = 'pip'
    finally:
        uninstall_completion()

    if deferred_pip_uninstall:
        return (
            '\nSeiscat uninstall has been scheduled using pip.\n'
            'This terminal may show pip output after seiscat exits.\n'
            'Managed completion snippets removed.\n'
            'For reinstall instructions, visit:\n'
            '  https://seiscat.seismicsource.org'
        )

    return (
        f'\nSeiscat uninstalled using {backend}.\n'
        'Managed completion snippets removed.\n'
        'For reinstall instructions, visit:\n'
        '  https://seiscat.seismicsource.org'
    )

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
OS-native service artifact generation and management for seiscat daemon mode.

Supports:
  - macOS: launchd plist (user LaunchAgents by default)
  - Linux: systemd unit + timer (user scope by default)

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import pathlib
import shutil
import subprocess
import sys

from .cycle import parse_interval_seconds
from ..utils import err_exit

# ---------------------------------------------------------------------------
# Service label / unit name
# ---------------------------------------------------------------------------

_LAUNCHD_LABEL = 'org.seismicsource.seiscat.daemon'
_SYSTEMD_SERVICE = 'seiscat-daemon.service'
_SYSTEMD_TIMER = 'seiscat-daemon.timer'


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _seiscat_exe():
    """Return the absolute path to the seiscat executable."""
    return shutil.which('seiscat')


def _seiscat_invocation(configfile):
    """
    Return the list [executable, 'daemon', '-c', configfile, 'run']
    suitable for embedding in service files.
    """
    if exe := _seiscat_exe():
        return [exe, 'daemon', '-c', configfile, 'run']
    return [
        sys.executable, '-m', 'seiscat', 'daemon', '-c', configfile, 'run'
    ]


# ---------------------------------------------------------------------------
# macOS – launchd plist
# ---------------------------------------------------------------------------

_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>ProgramArguments</key>
    <array>
{program_args}
    </array>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{log_file}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{path}</string>
    </dict>
</dict>
</plist>
"""


def _plist_program_args(invocation):
    lines = [f'        <string>{arg}</string>' for arg in invocation]
    return '\n'.join(lines)


def render_launchd_plist(config, configfile):
    """
    Render a launchd plist string for the daemon.

    :param config: seiscat config dict
    :param configfile: absolute path to the seiscat config file
    :returns: plist XML string
    """
    invocation = _seiscat_invocation(configfile)
    working_dir = str(pathlib.Path(configfile).resolve().parent)
    interval = config.get('daemon_interval', '15 minutes')
    interval_seconds = parse_interval_seconds(interval)
    log_file = config.get('daemon_log_file') or str(
        pathlib.Path.home() / 'Library' / 'Logs' / 'seiscat' / 'daemon.log'
    )
    return _PLIST_TEMPLATE.format(
        label=_LAUNCHD_LABEL,
        working_dir=working_dir,
        program_args=_plist_program_args(invocation),
        interval_seconds=interval_seconds,
        log_file=log_file,
        path=os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
    )


def _launchd_plist_path(system=False):
    """Return the Path where the plist file should be installed."""
    if system:
        return (
            pathlib.Path('/Library/LaunchDaemons') / f'{_LAUNCHD_LABEL}.plist'
        )
    return (
        pathlib.Path.home()
        / 'Library'
        / 'LaunchAgents'
        / f'{_LAUNCHD_LABEL}.plist'
    )


# ---------------------------------------------------------------------------
# Linux – systemd unit + timer
# ---------------------------------------------------------------------------

_SYSTEMD_SERVICE_TEMPLATE = """\
[Unit]
Description=seiscat daemon – one-shot catalog update cycle
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory={working_dir}
ExecStart={exec_start}
StandardOutput=append:{log_file}
StandardError=append:{log_file}
Environment=PATH={path}
"""

_SYSTEMD_TIMER_TEMPLATE = """\
[Unit]
Description=seiscat daemon timer

[Timer]
OnUnitActiveSec={interval}
Unit={service_name}
Persistent=true

[Install]
WantedBy=timers.target
"""


def render_systemd_service(config, configfile):
    """
    Render a systemd service unit string for the daemon.

    :param config: seiscat config dict
    :param configfile: absolute path to the seiscat config file
    :returns: unit file string
    """
    invocation = _seiscat_invocation(configfile)
    working_dir = str(pathlib.Path(configfile).resolve().parent)
    exec_start = ' '.join(invocation)
    log_file = config.get('daemon_log_file') or str(
        _xdg_state_dir() / 'daemon.log'
    )
    return _SYSTEMD_SERVICE_TEMPLATE.format(
        exec_start=exec_start,
        working_dir=working_dir,
        log_file=log_file,
        path=os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'),
    )


def render_systemd_timer(config):
    """
    Render a systemd timer unit string for the daemon.

    :param config: seiscat config dict
    :returns: timer unit file string
    """
    interval = config.get('daemon_interval', '15 minutes')
    interval_seconds = parse_interval_seconds(interval)
    return _SYSTEMD_TIMER_TEMPLATE.format(
        interval=f'{interval_seconds}s',
        service_name=_SYSTEMD_SERVICE,
    )


def _xdg_state_dir():
    """Return the XDG state home for seiscat."""
    if xdg := os.environ.get('XDG_STATE_HOME', ''):
        return pathlib.Path(xdg) / 'seiscat'
    return pathlib.Path.home() / '.local' / 'state' / 'seiscat'


def _systemd_unit_dir(system=False):
    """Return the Path where systemd unit files should be installed."""
    if system:
        return pathlib.Path('/etc/systemd/system')
    if xdg := os.environ.get('XDG_CONFIG_HOME', ''):
        return pathlib.Path(xdg) / 'systemd' / 'user'
    return pathlib.Path.home() / '.config' / 'systemd' / 'user'


# ---------------------------------------------------------------------------
# install-service
# ---------------------------------------------------------------------------

def install_service(config, configfile, system=False):
    """
    Generate and install service artifacts for the current OS.

    :param config: seiscat config dict
    :param configfile: absolute path to the seiscat config file
    :param system: if True install system-wide (requires elevated privileges)
    """
    if not config.get('daemon_enabled', False):
        err_exit(
            'daemon_enabled is False in the config file. '
            'Set daemon_enabled = True before installing the service.'
        )
    platform = sys.platform
    if platform == 'darwin':
        _install_launchd(config, configfile, system)
    elif platform.startswith('linux'):
        _install_systemd(config, configfile, system)
    else:
        err_exit(
            f'Unsupported platform: {platform}. '
            'Only macOS (launchd) and Linux (systemd) are supported.'
        )


def _install_launchd(config, configfile, system=False):
    """Install a launchd plist."""
    if system and os.geteuid() != 0:
        err_exit(
            'System-wide launchd service installation requires root. '
            'Re-run with sudo or omit --system for a per-user agent.'
        )
    plist_path = _launchd_plist_path(system)
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_content = render_launchd_plist(config, configfile)
    # Unload first if already loaded (idempotent)
    if plist_path.exists():
        _launchctl(['unload', str(plist_path)], check=False)
    plist_path.write_text(plist_content, encoding='utf-8')
    _launchctl(['load', str(plist_path)])
    print(f'Installed launchd plist: {plist_path}')
    print()
    print('Next steps:')
    print(f'  Check status : launchctl list {_LAUNCHD_LABEL}')
    print(f'  Run manually : launchctl start {_LAUNCHD_LABEL}')
    print('  Uninstall    : seiscat daemon uninstall-service')


def _install_systemd(config, configfile, system=False):
    """Install systemd service + timer units."""
    if system and os.geteuid() != 0:
        err_exit(
            'System-wide systemd service installation requires root. '
            'Re-run with sudo or omit --system for a per-user unit.'
        )
    unit_dir = _systemd_unit_dir(system)
    unit_dir.mkdir(parents=True, exist_ok=True)
    service_path = unit_dir / _SYSTEMD_SERVICE
    timer_path = unit_dir / _SYSTEMD_TIMER
    service_content = render_systemd_service(config, configfile)
    timer_content = render_systemd_timer(config)
    service_path.write_text(service_content, encoding='utf-8')
    timer_path.write_text(timer_content, encoding='utf-8')
    scope = [] if system else ['--user']
    _systemctl(scope + ['daemon-reload'])
    _systemctl(scope + ['enable', '--now', _SYSTEMD_TIMER])
    print(f'Installed systemd units in: {unit_dir}')
    print(f'  Service : {service_path.name}')
    print(f'  Timer   : {timer_path.name}')
    print()
    print('Next steps:')
    scope_flag = '' if system else ' --user'
    print(f'  Check status : systemctl{scope_flag} status {_SYSTEMD_TIMER}')
    print(f'  Run manually : systemctl{scope_flag} start {_SYSTEMD_SERVICE}')
    print('  Uninstall    : seiscat daemon uninstall-service')


# ---------------------------------------------------------------------------
# uninstall-service
# ---------------------------------------------------------------------------

def uninstall_service(config, system=False):
    """
    Remove the service artifacts installed by install_service.

    :param config: seiscat config dict (used for platform detection only)
    :param system: if True remove from system-wide locations
    """
    platform = sys.platform
    if platform == 'darwin':
        _uninstall_launchd(system)
    elif platform.startswith('linux'):
        _uninstall_systemd(system)
    else:
        err_exit(
            f'Unsupported platform: {platform}. '
            'Only macOS (launchd) and Linux (systemd) are supported.'
        )


def _uninstall_launchd(system=False):
    """Remove a launchd plist."""
    plist_path = _launchd_plist_path(system)
    if plist_path.exists():
        _launchctl(['unload', str(plist_path)], check=False)
        plist_path.unlink()
        print(f'Removed launchd plist: {plist_path}')
    else:
        print(f'No launchd plist found at: {plist_path}')


def _uninstall_systemd(system=False):
    """Remove systemd service + timer units."""
    unit_dir = _systemd_unit_dir(system)
    scope = [] if system else ['--user']
    for unit in [_SYSTEMD_TIMER, _SYSTEMD_SERVICE]:
        path = unit_dir / unit
        if path.exists():
            _systemctl(
                scope + ['disable', '--now', unit], check=False
            )
            path.unlink()
            print(f'Removed: {path}')
        else:
            print(f'Not found (skipping): {path}')
    _systemctl(scope + ['daemon-reload'], check=False)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def show_status(config):
    """
    Print service status and last-run metadata.

    :param config: seiscat config dict
    """
    from .cycle import _load_state, _lock_file_path, _read_lock, _pid_alive
    # --- last-run state ---
    state = _load_state(config)
    if last_run := state.get('last_run'):
        print('Last daemon run:')
        print(f'  Started at : {last_run.get("started_at", "unknown")}')
        print(f'  Status     : {last_run.get("status", "unknown")}')
        if stages := last_run.get('stages', {}):
            print('  Stages:')
            for name, info in stages.items():
                elapsed = info.get('elapsed_s', '')
                status = info.get('status', '')
                elapsed_str = f' ({elapsed}s)' if elapsed else ''
                print(f'    {name}: {status}{elapsed_str}')
    else:
        print('No daemon run recorded yet.')

    # --- lock file ---
    lock_path = _lock_file_path(config)
    if lock_path.exists():
        pid, ts = _read_lock(lock_path)
        if pid and _pid_alive(pid):
            print(f'\nLock held by running process: pid={pid}')
        else:
            print(f'\nStale lock file present: {lock_path}')
    else:
        print('\nNo lock file present (daemon is not running).')

    # --- OS service status ---
    platform = sys.platform
    print()
    if platform == 'darwin':
        plist_path = _launchd_plist_path()
        if plist_path.exists():
            print(f'launchd plist installed: {plist_path}')
            _launchctl(['list', _LAUNCHD_LABEL], check=False)
        else:
            print('launchd plist not installed.')
    elif platform.startswith('linux'):
        unit_dir = _systemd_unit_dir()
        timer_path = unit_dir / _SYSTEMD_TIMER
        if timer_path.exists():
            print(f'systemd timer installed: {timer_path}')
            _systemctl(['--user', 'status', _SYSTEMD_TIMER], check=False)
        else:
            print('systemd timer not installed.')
    else:
        print(f'OS service status not available on {platform}.')


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def _launchctl(args, check=True):
    """Run launchctl with *args*."""
    try:
        return subprocess.run(
            ['launchctl'] + args,
            capture_output=False,
            check=check,
        )
    except FileNotFoundError:
        err_exit('launchctl not found. Is this macOS?')
    except subprocess.CalledProcessError as exc:
        if check:
            err_exit(f'launchctl failed (exit {exc.returncode}).')
    return None


def _systemctl(args, check=True):
    """Run systemctl with *args*."""
    try:
        return subprocess.run(
            ['systemctl'] + args,
            capture_output=False,
            check=check,
        )
    except FileNotFoundError:
        err_exit('systemctl not found. Is this Linux with systemd?')
    except subprocess.CalledProcessError as exc:
        if check:
            err_exit(f'systemctl failed (exit {exc.returncode}).')
    return None


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------

def run_daemon_command(config):
    """
    Dispatch the daemon sub-command based on config['args'].daemon_action.

    :param config: seiscat config dict (must include 'args')
    """
    args = config['args']
    action = getattr(args, 'daemon_action', None)
    configfile = os.path.abspath(args.configfile)
    system = getattr(args, 'system', False)

    if action == 'run':
        from .cycle import run_daemon_cycle
        run_daemon_cycle(config)
    elif action == 'install-service':
        install_service(config, configfile, system=system)
    elif action == 'uninstall-service':
        uninstall_service(config, system=system)
    elif action == 'status':
        show_status(config)
    else:
        err_exit(f'Unknown daemon action: {action!r}')

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Run a user-defined command on a list of events.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import subprocess
import platform
from pathlib import Path
from .database.dbfunctions import (
    read_evids_and_versions_from_db, read_events_from_db
)
from .utils import ExceptionExit, err_exit


def run_command(config):
    """
    Execute a user-defined command for each event stored in the database.

    The command can be a shell script or executable.
    On Windows, the function automatically detects and uses the appropriate
    interpreter based on the file extension:

    - `.ps1` → PowerShell
    - `.py`  → Python
    - `.bat` / `.cmd` → CMD shell

    On Unix-like systems (Linux/macOS), the command is executed directly
    through the system shell. For each event, all event fields are exported
    as environment variables, allowing scripts to access event data.

    Database access supports concurrent processes, enabling multiple
    instances to modify the database safely while commands are being run.

    :param config: Configuration object
    :type config: dict
    """
    args = config['args']
    command = args.command
    command_path = Path(command)
    ext = command_path.suffix.lower()
    is_windows = platform.system() == 'Windows'
    # Get list of event IDs and versions without WHERE clause to avoid
    # concurrency issues
    with ExceptionExit():
        evids_and_versions = read_evids_and_versions_from_db(config)
    # Query events one by one to allow concurrent database modifications
    for evid, ver in evids_and_versions:
        try:
            event = read_events_from_db(config, eventid=evid, version=ver)[0]
        except IndexError:
            continue
        print(f'Running {command} on event {evid} version {ver}')
        # Merge event data with environment variables
        event_env = {k: str(v) for k, v in event.items()}
        env = {**os.environ, **event_env}
        # Determine command execution method based on platform and file type
        run_cmd = []
        shell_flag = False
        if is_windows:
            if ext == '.ps1':
                run_cmd = [
                    'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                    '-File', str(command_path)
                ]
                shell_flag = False
            elif ext == '.py':
                run_cmd = ['python', str(command_path)]
                shell_flag = False
            elif ext in {'.bat', '.cmd'}:
                run_cmd = f'"{command_path}"'
                shell_flag = True
        else:
            run_cmd = command
            shell_flag = False
        if not run_cmd:
            err_exit(f'Unsupported script type: {command}')
        # Execute the command
        try:
            subprocess.run(run_cmd, env=env, shell=shell_flag, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Command {command} failed with exit status {e.returncode}')

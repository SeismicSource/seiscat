# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Run a user-defined command on a list of events.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import subprocess
from .database.dbfunctions import read_events_from_db
from .utils import ExceptionExit


def run_command(config):
    """
    Run a user-defined command on a list of events.

    :param config: config object
    :type config: dict
    """
    args = config['args']
    command = args.command
    with ExceptionExit():
        events = read_events_from_db(config)
    for event in events:
        print(f'Running {command} on event {event["evid"]}')
        event_str = {k: str(v) for k, v in event.items()}
        env = {**os.environ, **event_str}
        try:
            subprocess.run(command, shell=True, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Command {command} failed with exit status {e.returncode}')

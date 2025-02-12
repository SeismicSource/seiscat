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
from .database.dbfunctions import (
    read_evids_and_versions_from_db, read_events_from_db
)
from .utils import ExceptionExit


def run_command(config):
    """
    Run a user-defined command on a list of events.
    This function supports concurrent processes, all modifying the database.

    :param config: config object
    :type config: dict
    """
    args = config['args']
    command = args.command
    # First, just get the list of evids and versions, without using the "where"
    # clause, to avoid concurrency problems
    with ExceptionExit():
        evids_and_versions = read_evids_and_versions_from_db(config)
    # Then, query the events one by one, now using the "where" clause
    # This allows for concurrent processes to modify the database while
    # we're querying the events
    for evid, ver in evids_and_versions:
        try:
            event = read_events_from_db(config, eventid=evid, version=ver)[0]
        except IndexError:
            continue
        print(f'Running {command} on event {evid} version {ver}')
        event_str = {k: str(v) for k, v in event.items()}
        env = {**os.environ, **event_str}
        try:
            subprocess.run(command, shell=True, env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f'Command {command} failed with exit status {e.returncode}')

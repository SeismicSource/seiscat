#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Main script for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import sys
import contextlib
# NOTE: other modules are lazy-imported to speed up startup time
# pylint: disable=import-outside-toplevel, relative-beyond-top-level


def run():
    """Run seiscat."""
    from .config import parse_arguments
    args = parse_arguments()
    from .utils import set_debug
    env_debug = os.environ.get('SC_DEBUG', '')
    set_debug(env_debug.lower() in ('1', 'true', 'yes', 'on'))
    from .config import parse_configspec, read_config, write_sample_config
    configspec = parse_configspec()
    if args.action == 'sampleconfig':
        write_sample_config(configspec, 'seiscat')
        sys.exit(0)
    elif args.action == 'samplescript':
        from .utils import write_sample_script
        write_sample_script()
        sys.exit(0)
    if args.action == 'logo':
        from .utils import print_logo
        print_logo()
        sys.exit(0)
    config = read_config(args.configfile, configspec)
    config['args'] = args
    if args.action == 'initdb':
        from .database.feeddb import feeddb
        feeddb(config, initdb=True)
    elif args.action == 'updatedb':
        from .database.feeddb import feeddb
        feeddb(config, initdb=False)
    elif args.action == 'editdb':
        from .database.editdb import editdb
        editdb(config)
    elif args.action == 'get':
        from .database import seiscat_get
        seiscat_get(config)
    elif args.action == 'set':
        from .database import seiscat_set
        seiscat_set(config)
    elif args.action == 'fetchdata':
        fetch_event = args.event or args.both
        fetch_data = args.data or args.both
        if fetch_event:
            from .fetchdata.event_details import fetch_event_details
            fetch_event_details(config)
        if fetch_data:
            from .fetchdata.event_waveforms import fetch_event_waveforms
            fetch_event_waveforms(config)
    elif args.action == 'print':
        from .print import print_catalog
        print_catalog(config)
    elif args.action == 'plot':
        from .plot.plot_map import plot_catalog_map
        plot_catalog_map(config)
    elif args.action == 'run':
        from .run_command import run_command
        run_command(config)


def main():
    """Main function. Catch KeyboardInterrupt."""
    with contextlib.suppress(ImportError):
        # Avoid broken pipe errors, e.g., when piping output to head
        # Note: SIGPIPE is not available on Windows
        from signal import signal, SIGPIPE, SIG_DFL
        signal(SIGPIPE, SIG_DFL)
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(1)

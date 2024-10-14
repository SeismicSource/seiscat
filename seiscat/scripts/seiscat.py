#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Main script for seiscat.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
# NOTE: other modules are lazy-imported to speed up startup time
# pylint: disable=import-outside-toplevel, relative-beyond-top-level


def run():
    """Run seiscat."""
    from ..parse_arguments import parse_arguments
    args = parse_arguments()
    from ..utils import parse_configspec, read_config,  write_sample_config
    configspec = parse_configspec()
    if args.action == 'sampleconfig':
        write_sample_config(configspec, 'seiscat')
        sys.exit(0)
    config = read_config(args.configfile, configspec)
    config['args'] = args
    if args.action == 'initdb':
        from ..feeddb import feeddb
        feeddb(config, initdb=True)
    elif args.action == 'updatedb':
        from ..feeddb import feeddb
        feeddb(config, initdb=False)
    elif args.action == 'editdb':
        from ..editdb import editdb
        editdb(config)
    elif args.action == 'download':
        download_event = args.event or args.both
        download_data = args.data or args.both
        if download_event:
            from ..download_event_details import download_event_details
            download_event_details(config)
        if download_data:
            from ..download_event_waveforms import download_event_waveforms
            download_event_waveforms(config)
    elif args.action == 'print':
        from ..print import print_catalog
        print_catalog(config)
    elif args.action == 'plot':
        from ..plot_map import plot_catalog_map
        plot_catalog_map(config)


def main():
    """Main function. Catch KeyboardInterrupt."""
    # Avoid broken pipe errors, e.g., when piping output to head
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE, SIG_DFL)
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(1)

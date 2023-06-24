#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Main script for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
# NOTE: other modules are lazy-imported to speed up startup time


def run():
    from ..parse_arguments import parse_arguments
    """Run seiscat."""
    args = parse_arguments()
    from ..utils import parse_configspec, read_config,  write_sample_config
    configspec = parse_configspec()
    if args.action == 'sampleconfig':
        write_sample_config(configspec, 'seiscat')
        sys.exit(0)
    config = read_config(args.configfile, configspec)
    config['args'] = args
    if args.action == 'initdb':
        from ..download_and_store import download_and_store
        download_and_store(config, initdb=True)
    elif args.action == 'updatedb':
        from ..download_and_store import download_and_store
        download_and_store(config, initdb=False)
    elif args.action == 'editdb':
        from ..editdb import editdb
        editdb(config)
    elif args.action == 'print':
        from ..print import print_catalog
        print_catalog(config)
    elif args.action == 'plot':
        from ..plot import plot_catalog_map
        plot_catalog_map(config)


def main():
    """Main function. Catch KeyboardInterrupt."""
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(1)

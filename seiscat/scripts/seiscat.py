#!/usr/bin/env python
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
import argparse
import argcomplete
from .._version import get_versions
# NOTE: most modules are lazy-imported to speed up startup time


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Keep a local seismic catalog.')
    subparser = parser.add_subparsers(dest='action')
    subparser.add_parser('initdb', help='initialize database')
    subparser.add_parser('updatedb', help='update database')
    subparser.add_parser('print', help='print catalog')
    plot_parser = subparser.add_parser('plot', help='plot catalog map')
    plot_parser.add_argument(
        '-s',
        '--scale',
        type=float,
        default=10,
        help='scale factor for marker size (default: %(default)s)'
    )
    subparser.add_parser('sampleconfig', help='write sample config file')
    parser.add_argument(
        '-c',
        '--configfile',
        type=str,
        default='seiscat.conf',
        help='config file for data sources and processing params'
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f"%(prog)s {get_versions()['version']}",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        sys.exit(0)
    return args


def download_and_store(config, initdb):
    """
    Download events and store them in the database.

    :param config: config object
    :param initdb: if True, create new database file
    """
    from ..db import check_db_exists, write_catalog_to_db
    from ..fdsnws import open_fdsn_connection, query_events
    check_db_exists(config, initdb)
    client = open_fdsn_connection(config)
    cat = query_events(client, config, first_query=initdb)
    write_catalog_to_db(cat, config, initdb)


def run():
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
        download_and_store(config, initdb=True)
    elif args.action == 'updatedb':
        download_and_store(config, initdb=False)
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

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
from .._version import get_versions
from ..fdsnws import open_fdsn_connection, select_events
from ..db import check_db_exists, write_catalog_to_db
from ..utils import (
    parse_configspec, read_config, validate_config, write_sample_config,
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run seiscat.')
    subparser = parser.add_subparsers(dest='action')
    subparser.add_parser('initdb', help='initialize database')
    subparser.add_parser('updatedb', help='update database')
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
    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        sys.exit(0)
    return args


def main():
    args = parse_arguments()
    configspec = parse_configspec()
    if args.action == 'sampleconfig':
        write_sample_config(configspec, 'seiscat')
        sys.exit(0)
    config = read_config(args.configfile, configspec)
    validate_config(config)
    client = open_fdsn_connection(config)
    if args.action == 'initdb':
        check_db_exists(config)
        cat = select_events(client, config, first_query=True)
        write_catalog_to_db(cat, config, replace=True)
    elif args.action == 'updatedb':
        cat = select_events(client, config, first_query=False)
        write_catalog_to_db(cat, config, replace=False)

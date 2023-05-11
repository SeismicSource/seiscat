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
from ..utils import (
    parse_configspec, read_config, validate_config, write_sample_config
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run seiscat.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-c',
        '--configfile',
        type=str,
        help='config file for data sources and processing params'
    )
    group.add_argument(
        '-s',
        '--sampleconfig',
        default=False,
        action='store_true',
        required=False,
        help='write sample config file to current directory and exit'
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f"%(prog)s {get_versions()['version']}",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    configspec = parse_configspec()
    if args.sampleconfig:
        write_sample_config(configspec, 'seiscat')
        sys.exit(0)
    config = read_config(args.configfile, configspec)
    validate_config(config)
    print(config)

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Argument parsing for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
import argparse
import argcomplete
from ._version import get_versions
# NOTE: most modules are lazy-imported to speed up startup time


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Keep a local seismic catalog.')
    subparser = parser.add_subparsers(dest='action')
    subparser.add_parser('initdb', help='initialize database')
    subparser.add_parser('updatedb', help='update database')
    editdb_parser = subparser.add_parser('editdb', help='edit database')
    editdb_parser.add_argument(
        'eventid', nargs=1, help='event ID to edit')
    editdb_parser.add_argument(
        '-v',
        '--version',
        type=int,
        default=None,
        help='event version to edit, required if more than one version'
    )
    editdb_parser.add_argument(
        '-s',
        '--set',
        type=str,
        metavar='KEY=VALUE',
        nargs='+',
        help='set event attributes. Multiple KEY=VALUE pairs can be given '
             '(e.g., time=2022-01-01T00:00:00.0Z lat=12.0 lon=-3.0 depth=20.0)'
    )
    editdb_parser.add_argument(
        '-r',
        '--replicate',
        action='store_true',
        default=False,
        help='replicate event (will be assigned a new version number)'
    )
    editdb_parser.add_argument(
        '-d',
        '--delete',
        action='store_true',
        default=False,
        help='delete event'
    )
    editdb_parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        default=False,
        help='force edit (skip confirmation)'
    )
    versions_parser = argparse.ArgumentParser(add_help=False)
    versions_parser.add_argument(
        '-a',
        '--allversions',
        action='store_true',
        default=False,
        help='show all versions of each event (default: %(default)s)'
    )
    print_parser = subparser.add_parser(
        'print', parents=[versions_parser], help='print catalog')
    print_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to print (only used for table format)')
    print_parser.add_argument(
        '-f',
        '--format',
        type=str,
        default='table',
        choices=['table', 'stats'],
        help='output format (default: %(default)s)'
    )
    print_parser.add_argument(
        '-r',
        '--reverse',
        action='store_true',
        default=False,
        help='print catalog in reverse order (default: %(default)s)'
    )
    plot_parser = subparser.add_parser(
        'plot', parents=[versions_parser], help='plot catalog map')
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

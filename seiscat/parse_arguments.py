# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Argument parsing for seiscat.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
import textwrap
import argparse
import argcomplete
from ._version import get_versions


def _get_db_cursor(configfile):
    """
    Get a cursor to the database.

    :param configfile: path to config file
    :return: cursor to the database
    """
    try:
        fp = open(configfile, 'r', encoding='utf-8')
    except FileNotFoundError:
        return None
    try:
        db_file = [
            line.split('=')[1].strip() for line in fp
            if line.startswith('db_file')][0]
    except IndexError:
        db_file = 'seiscat.sqlite'
    try:
        open(db_file, 'r', encoding='utf-8')
    except FileNotFoundError:
        return None
    # pylint: disable=import-outside-toplevel
    import sqlite3  # lazy import to speed up startup time
    conn = sqlite3.connect(db_file)
    return conn.cursor()


def _evid_completer(prefix, parsed_args, **_kwargs):
    """
    Completer for event IDs.

    :param prefix: prefix to complete
    :param parsed_args: parsed arguments
    :param kwargs: keyword arguments
    :return: list of event IDs
    """
    if _evid_completer.db_cursor is None:
        _evid_completer.db_cursor = _get_db_cursor(parsed_args.configfile)
    if _evid_completer.db_cursor is None:
        return []
    _evid_completer.db_cursor.execute(
        'SELECT evid FROM events WHERE evid LIKE ?', (f'{prefix}%',)
    )
    return [row[0] for row in _evid_completer.db_cursor.fetchall()]
_evid_completer.db_cursor = None  # noqa: E305


class NewlineHelpFormatter(argparse.HelpFormatter):
    """
    Custom help formatter that preserves newlines in help messages.
    """
    def _split_lines(self, text, width):
        lines = []
        for line in text.splitlines():  # Split the text by newlines first
            if len(line) > width:
                # Use textwrap to wrap lines that are too long
                wrap_lines = textwrap.wrap(line, width)
                lines.extend(wrap_lines)
            else:
                # For lines that are short enough, just add them as they are
                lines.append(line)
        return lines


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Keep a local seismic catalog.')
    subparser = parser.add_subparsers(dest='action')
    fromfile_parser = argparse.ArgumentParser(add_help=False)
    fromfile_parser.add_argument(
        '-f',
        '--fromfile',
        type=str,
        metavar='FILENAME',
        help='read events from a CSV file'
    )
    unit_parser = argparse.ArgumentParser(add_help=False)
    unit_parser.add_argument(
        '-d',
        '--depth_units',
        type=str,
        default=None,
        choices=['m', 'km'],
        help='depth units (default: autodetect)'
    )
    subparser.add_parser(
        'initdb', parents=[fromfile_parser, unit_parser],
        help='initialize database')
    subparser.add_parser(
        'updatedb', parents=[fromfile_parser, unit_parser],
        help='update database')
    editdb_parser = subparser.add_parser('editdb', help='edit database')
    editdb_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to edit. Use ALL to edit all events'
    ).completer = _evid_completer
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
             '(e.g., -s time=2022-01-01T00:00:00.0Z lat=12.0 lon=-3.0 '
             'depth=20.0)'
    )
    editdb_parser.add_argument(
        '-i',
        '--increment',
        type=str,
        metavar='KEY=INCREMENT',
        nargs='+',
        help='increment a numeric event attribute by a specified amount '
             '(e.g., -i depth=3.0). Use a negative INCREMENT to decrement '
             '(e.g., -i depth=-5.0)'
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
    where_parser = argparse.ArgumentParser(add_help=False)
    where_parser.add_argument(
        '-w',
        '--where',
        type=str,
        metavar='KEY OP VALUE [AND|OR KEY OP VALUE ...]',
        help='filter events based on one or more conditions.\n\n'
             'KEY is the attribute name, OP is the comparison operator \n'
             '(=, <, >, <=, >=, !=), and VALUE is the value to compare to.\n'
             'Multiple KEY OP VALUE pairs can be given, separated by the\n'
             'logical operators AND or OR (uppercase or lowecase).\n'
             'Examples:\n'
             '-w "depth < 10.0 AND mag >= 3.0"\n'
             '-w "depth < 10.0 OR depth > 100.0"\n'
             '-w "evid = aa1234bb"\n\n'
             'Note that the comparison operators must be quoted to avoid\n'
             'interpretation by the shell.\n'
    )
    download_parser = subparser.add_parser(
        'download', parents=[versions_parser, where_parser],
        help='download full event details and/or waveform data and metadata',
        formatter_class=NewlineHelpFormatter
    )
    download_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to download (default: all events)'
    ).completer = _evid_completer
    group = download_parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-e',
        '--event',
        action='store_true',
        default=False,
        help='download full event details to a QuakeML file '
             '(default: %(default)s)'
    )
    group.add_argument(
        '-d',
        '--data',
        action='store_true',
        default=False,
        help='download waveform data and metadata to miniSEED and StationXML '
             'files'
    )
    group.add_argument(
        '-b',
        '--both',
        action='store_true',
        default=False,
        help='download both event details and waveform data and metadata'
    )
    download_parser.add_argument(
        '-o',
        '--overwrite_existing',
        action='store_true',
        default=False,
        help='overwrite existing QuakeML files (default: %(default)s). '
             'Only used when downloading event details'
    )
    print_parser = subparser.add_parser(
        'print', parents=[versions_parser, where_parser],
        help='print catalog',
        formatter_class=NewlineHelpFormatter
    )
    print_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to print (only used for table format)'
    ).completer = _evid_completer
    print_parser.add_argument(
        '-f',
        '--format',
        type=str,
        default='table',
        choices=['table', 'csv', 'stats'],
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
        'plot', parents=[versions_parser, where_parser],
        help='plot catalog map',
        formatter_class=NewlineHelpFormatter
    )
    plot_parser.add_argument(
        '-m',
        '--maptype',
        type=str,
        default='cartopy',
        choices=['cartopy', 'folium'],
        help='map type (default: %(default)s)'
    )
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

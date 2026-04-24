# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Argument parsing for seiscat.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import sys
import textwrap
import argparse
import platform
import argcomplete
from rich_argparse import RichHelpFormatter
from rich.console import Console
from rich.panel import Panel
from .._version import get_versions
from ..utils.logo import SEISCAT_LOGO_SMALL
from .autocompletion import (
    evid_completer,
    sortby_completer,
    colormap_completer,
)


def print_where_help_and_exit():
    """Print detailed help for the --where option and exit."""
    console = Console()
    help_text = """[bold]WHERE filter expression[/bold]

Filter events based on one or more conditions.

[bold]Syntax[/bold]
KEY OP VALUE [AND|OR KEY OP VALUE ...]

Where:
  [cyan]KEY[/cyan]   - attribute name
  [cyan]OP[/cyan]    - comparison operator (=, <, >, <=, >=, !=)
  [cyan]VALUE[/cyan] - value to compare to

[bold]Examples[/bold]
  -w "depth < 10.0 AND mag >= 3.0"
  -w "depth < 10.0 OR depth > 100.0"
  -w "evid = aa1234bb"
  -w "mag"         (shorthand for [italic]mag IS NOT NULL AND mag != 0[/italic])
  -w "mag != None" (matches non-null values, including 0)

[bold]Note[/bold]
Comparison operators must be quoted to avoid shell interpretation.
A bare key (e.g., [cyan]mag[/cyan]) uses SQL truthiness, so it means
[italic]non-null and non-zero[/italic]."""  # noqa: E501 (ignore long line)
    panel = Panel(help_text, title="--where", expand=False, padding=(1, 2))
    console.print(panel)
    sys.exit(0)


class WhereHelpAction(argparse.Action):
    """Custom action for --where-help that displays detailed help and exits."""
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print_where_help_and_exit()


class CustomArgumentParser(argparse.ArgumentParser):
    """Custom parser that adds helpful hints to error messages."""
    def error(self, message):
        # Add hint about --where-help if it's a --where error
        if '--where' in message or '-w' in message:
            message += '\n(see --where-help for details)'
        super().error(message)


class SubcommandHelpFormatter(RichHelpFormatter):
    """
    Custom help formatter that removes the list of subcommands from the help
    message.

    See: https://stackoverflow.com/a/13429281/2021880
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

    def _fill_text(self, text, width, indent):
        """Preserve explicit newlines in description/epilog text."""
        lines = []
        for line in text.splitlines():
            if not line.strip():
                lines.append('')
                continue
            lines.extend(textwrap.wrap(
                line,
                width,
                replace_whitespace=False,
                drop_whitespace=False
            ))
        return '\n'.join(lines)

    def _rich_fill_text(self, text, width, indent):
        """Preserve explicit newlines when Rich renders description text."""
        raw_lines = text.plain.splitlines()
        if not raw_lines:
            rendered = text[:0]
            rendered.append('\n\n')
            return rendered

        rendered = text[:0]
        indent_plain = (
            indent.plain if hasattr(indent, 'plain') else str(indent)
        )
        for idx, line in enumerate(raw_lines):
            if line.strip():
                wrapped_lines = textwrap.wrap(
                    line,
                    width=width,
                    replace_whitespace=False,
                    drop_whitespace=False
                ) or ['']
                for widx, wrapped_line in enumerate(wrapped_lines):
                    line_text = text[:0] + indent_plain + wrapped_line
                    for highlight in self.highlights:
                        line_text.highlight_regex(
                            highlight,
                            style_prefix='argparse.'
                        )
                    rendered.append_text(line_text)
                    if widx < len(wrapped_lines) - 1:
                        rendered.append('\n')
            if idx < len(raw_lines) - 1:
                rendered.append('\n')
        rendered.append('\n\n')
        return rendered

    def _format_action(self, action):
        parts = super()._format_action(action)
        if action.nargs == argparse.PARSER:
            parts = '\n'.join(parts.split('\n')[1:])
        return parts


def _get_parent_parsers():
    """Get a dictionary of parent parsers."""
    configfile_parser = argparse.ArgumentParser(add_help=False)
    configfile_parser.add_argument(
        '-c',
        '--configfile',
        type=str,
        default='seiscat.conf',
        help='config file for data sources and processing params'
    )
    fromfile_parser = argparse.ArgumentParser(add_help=False)
    fromfile_parser.add_argument(
        '-f',
        '--fromfile',
        type=str,
        metavar='FILENAME',
        nargs='+',
        help='read events from file(s). '
             'Accepts multiple filenames. '
             'Tries CSV format first, then falls back to '
             'ObsPy format auto-detection (QuakeML, SC3ML, NLLOC, etc.)'
    )
    fromfile_parser.add_argument(
        '-d',
        '--delimiter',
        type=str,
        default=None,
        help='CSV delimiter (default: autoset). '
             'Use "\\t" for tab or " " for space. '
             'Only used for CSV files.'
    )
    fromfile_parser.add_argument(
        '-n',
        '--column_names',
        type=str,
        default=None,
        nargs='+',
        help='column names in the CSV file (default: autodetect). '
             'Only used for CSV files.'
    )
    fromfile_parser.add_argument(
        '-x',
        '--missing-value',
        dest='no_value',
        type=str,
        default=None,
        nargs='+',
        metavar='VALUE',
        help='one or more values/strings to treat as missing in CSV input '
             '(e.g., --missing-value -999; '
             '--missing-value -999 N/A). Only used for CSV files.'
    )
    unit_parser = argparse.ArgumentParser(add_help=False)
    unit_parser.add_argument(
        '-z',
        '--depth_units',
        type=str,
        default=None,
        choices=['m', 'km'],
        help='depth units (default: autodetect)'
    )
    versions_parser = argparse.ArgumentParser(add_help=False)
    versions_parser.add_argument(
        '-a',
        '--allversions',
        action='store_true',
        default=False,
        help='consider all versions of each event (default: %(default)s)'
    )
    where_parser = CustomArgumentParser(add_help=False)
    where_parser.add_argument(
        '-w',
        '--where',
        type=str,
        metavar='EXPR',
        help='filter expression (use --where-help for details)'
    )
    where_parser.add_argument(
        '--where-help',
        action=WhereHelpAction,
        help='show detailed help for the --where option and exit'
    )
    reverse_parser = argparse.ArgumentParser(add_help=False)
    reverse_parser.add_argument(
        '-r',
        '--reverse',
        action='store_true',
        default=False,
        help='output catalog in reverse order (default: %(default)s)'
    )
    sortby_parser = argparse.ArgumentParser(add_help=False)
    sortby_parser.add_argument(
        '--sortby',
        type=str,
        default='time',
        help='field to sort by (default: %(default)s). '
             'Common fields: time, lat, lon, depth, mag, evid. '
             'Use any field name from the database.'
    ).completer = sortby_completer
    color_parser = argparse.ArgumentParser(add_help=False)
    color_parser.add_argument(
        '--colorby',
        type=str,
        default=None,
        metavar='FIELD',
        help='attribute used to color markers. '
             'Use any numeric field from the database.'
    ).completer = sortby_completer
    color_parser.add_argument(
        '--colormap',
        type=str,
        default='viridis',
        metavar='NAME',
        help='Matplotlib colormap name used for marker colors '
             '(default: %(default)s). '
             'Examples: viridis, plasma, inferno, cividis. '
             'See https://matplotlib.org/'
             'stable/users/explain/colors/colormaps.html'
    ).completer = colormap_completer
    crop_parser = argparse.ArgumentParser(add_help=False)
    crop_parser.add_argument(
        '-C', '--crop',
        action='store_true',
        default=False,
        help='when reading from file, crop the catalog to the geographic, '
             'depth and magnitude selection criteria defined in the '
             'configuration file (default: %(default)s). '
             'Has no effect when importing from FDSN, where the bounding '
             'box is already applied during the query.'
    )
    return {
        'configfile_parser': configfile_parser,
        'fromfile_parser': fromfile_parser,
        'unit_parser': unit_parser,
        'versions_parser': versions_parser,
        'where_parser': where_parser,
        'reverse_parser': reverse_parser,
        'sortby_parser': sortby_parser,
        'color_parser': color_parser,
        'crop_parser': crop_parser,
    }


def _add_initdb_parser(subparser, parents):
    """Add the initdb subparser."""
    initdb_parser = subparser.add_parser(
        'initdb',
        parents=[
            parents['configfile_parser'],
            parents['fromfile_parser'],
            parents['unit_parser'],
            parents['crop_parser'],
        ],
        formatter_class=RichHelpFormatter,
        help='initialize database')
    initdb_parser.add_argument(
        '--csv-extra-columns',
        action='store_true',
        default=False,
        help='when importing CSV files, add non-standard CSV columns '
             'to the database as TEXT columns and populate them '
             '(default: %(default)s)'
    )


def _add_updatedb_parser(subparser, parents):
    """Add the updatedb subparser."""
    subparser.add_parser(
        'updatedb',
        parents=[
            parents['configfile_parser'],
            parents['fromfile_parser'],
            parents['unit_parser'],
            parents['crop_parser'],
        ],
        formatter_class=RichHelpFormatter,
        help='update database')


def _add_editdb_parser(subparser, parents):
    """Add the editdb subparser."""
    editdb_parser = subparser.add_parser(
        'editdb',
        parents=[
            parents['configfile_parser'],
            parents['where_parser'],
        ],
        formatter_class=RichHelpFormatter,
        help='edit database')
    editdb_parser.add_argument(
        'eventid',
        nargs='?',
        help='event ID to edit. Use ALL to edit all events'
    ).completer = evid_completer
    editdb_parser.add_argument(
        'event_version',
        nargs='?',
        type=int,
        default=None,
        help='event version to edit, required if more than one version'
    )
    editdb_parser.add_argument(
        '-s',
        '--set',
        type=str,
        metavar='KEY=VALUE',
        action='append',
        help='Set event attributes. Use multiple -s options for multiple '
             'KEY=VALUE pairs (e.g., -s time=2022-01-01T00:00:00.0Z '
             '-s lat=12.0 -s lon=-3.0 -s depth=20.0)'
    )
    editdb_parser.add_argument(
        '-i',
        '--increment',
        type=str,
        metavar='KEY=INCREMENT',
        action='append',
        help='increment a numeric event attribute by a specified amount '
             '(e.g., -i depth=3.0). Use a negative INCREMENT to decrement '
             '(e.g., -i depth=-5.0). Use multiple -i options for multiple '
             'KEY=INCREMENT pairs (e.g., -i depth=3.0 -i mag=-0.5). '
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
        '--add-column',
        type=str,
        metavar='NAME[:TYPE]',
        default=None,
        help='add a column to the events table. TYPE is optional and '
             'defaults to TEXT. Allowed types: TEXT, INTEGER, REAL, '
             'NUMERIC, BLOB'
    )
    editdb_parser.add_argument(
        '--delete-column',
        type=str,
        metavar='NAME',
        default=None,
        help='delete a column from the events table '
             '(default columns are protected)'
    )
    editdb_parser.add_argument(
        '--rename-column',
        type=str,
        metavar='OLD=NEW',
        default=None,
        help='rename a column in the events table '
             '(default columns are protected)'
    )
    editdb_parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        default=False,
        help='force edit (skip confirmation)'
    )


def _add_cropdb_parser(subparser, parents):
    """Add the cropdb subparser."""
    subparser.add_parser(
        'cropdb',
        parents=[
            parents['configfile_parser'],
        ],
        formatter_class=RichHelpFormatter,
        help='crop the database to the selection criteria in the config file'
    )


def _add_fetchdata_parser(subparser, parents):
    """Add the fetchdata subparser."""
    fetchdata_parser = subparser.add_parser(
        'fetchdata',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser']
        ],
        help='fetch full event details and/or waveform data and metadata',
        formatter_class=RichHelpFormatter
    )
    fetchdata_parser.add_argument(
        '-s', '--sds',
        metavar='SDS_DIR',
        type=str,
        help='fetch waveform data from a local SDS archive'
    )
    fetchdata_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to download (default: all events)'
    ).completer = evid_completer
    group = fetchdata_parser.add_mutually_exclusive_group(required=True)
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
    fetchdata_parser.add_argument(
        '-o',
        '--overwrite_existing',
        action='store_true',
        default=False,
        help='overwrite existing QuakeML files (default: %(default)s). '
             'Only used when downloading event details'
    )


def _add_print_parser(subparser, parents):
    """Add the print subparser."""
    print_parser = subparser.add_parser(
        'print',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser'],
            parents['sortby_parser'],
            parents['reverse_parser']
        ],
        help='print catalog',
        formatter_class=RichHelpFormatter
    )
    print_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to print'
    ).completer = evid_completer
    print_parser.add_argument(
        '-f',
        '--format',
        type=str,
        default='table',
        choices=['table', 'stats'],
        help='output format (default: %(default)s)'
    )
    print_parser.add_argument(
        '--max-col-width',
        type=int,
        default=40,
        metavar='N',
        help='maximum column width in the interactive table pager '
             '(default: %(default)s; use 0 to disable truncation)'
    )


def _add_export_parser(subparser, parents):
    """Add the export subparser."""
    export_parser = subparser.add_parser(
        'export',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser'],
            parents['sortby_parser'],
            parents['reverse_parser']
        ],
        help='export catalog to file',
        formatter_class=RichHelpFormatter
    )
    formats = ['csv', 'json', 'kml']
    export_parser.add_argument(
        '-f',
        '--format',
        type=str,
        choices=formats,
        default=None,
        help=(
            f'Output format ({", ".join(formats)}). '
            'If specified, this option takes precedence over the extension '
            'of the output file. '
            'If omitted, the format is inferred from the outfile extension.'
        )
    )
    export_parser.add_argument(
        '-s',
        '--scale',
        type=float,
        default=5.0,
        help=(
            'Scale factor for marker size (default: %(default)s). '
            'Only valid for KML output.'
        )
    )
    export_parser.add_argument(
        'outfile',
        type=str,
        help=(
            'Path to the output file. '
            'The file format is inferred from the filename extension '
            f'(e.g., {", ".join(f".{fmt}" for fmt in formats)}), '
            'unless overridden by --format.'
        )
    )


def _add_plot_parser(subparser, parents):
    """Add the plot subparser."""
    plot_parser = subparser.add_parser(
        'plot',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser'],
            parents['sortby_parser'],
            parents['reverse_parser'],
            parents['color_parser']
        ],
        help='plot catalog map',
        formatter_class=RichHelpFormatter
    )
    plot_parser.add_argument(
        '-b',
        '--backend',
        type=str,
        default='cartopy',
        choices=['cartopy', 'folium', 'plotly'],
        help='map backend (default: %(default)s)'
    )
    plot_parser.add_argument(
        '-s',
        '--scale',
        type=float,
        default=10,
        help='scale factor for marker size (default: %(default)s)'
    )
    plot_parser.add_argument(
        '-t',
        '--time_slider',
        action='store_true',
        default=False,
        help='add a time slider to the plot (default: %(default)s), '
             'only used for Plotly maps'
    )
    plot_parser.add_argument(
        '-o', '--out-file',
        type=str,
        default=None,
        help='output file for the plot (default: show on screen). '
             'For cartopy maps, the output file format is determined by '
             'the file extension (e.g., .png, .pdf, .svg). '
             'For folium and plotly maps, the output file should have '
             'a .html extension. '
    )
    plot_parser.add_argument(
        '--threshold',
        type=str,
        default=None,
        metavar='VALUE',
        help='threshold above which markers have an outline. '
             'Default: None (all markers have an outline). '
             'Only used with --colorby and --backend cartopy. '
             'For --colorby time, VALUE can be either epoch seconds '
             'or an ISO datetime (e.g., 2026-04-08T12:00:00Z).'
    )


def _add_timeline_parser(subparser, parents):
    """Add the timeline subparser."""
    timeline_parser = subparser.add_parser(
        'timeline',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser'],
            parents['color_parser'],
        ],
        help='plot a timeline of the earthquake catalog',
        formatter_class=RichHelpFormatter
    )
    mode_group = timeline_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '-A',
        '--attribute',
        type=str,
        default='mag',
        metavar='FIELD',
        help='event attribute to plot on the Y axis (default: %(default)s). '
             'Use any numeric field from the database (e.g., depth, lat, lon).'
    ).completer = sortby_completer
    mode_group.add_argument(
        '-C',
        '--count',
        action='store_true',
        default=False,
        help='plot event count per time bin instead of a scatter of an '
             'attribute (default: %(default)s)'
    )
    timeline_parser.add_argument(
        '-B',
        '--bins',
        type=str,
        default=None,
        metavar='SPEC',
        help='bin width for count mode (default: auto). '
             'Accepted formats: integer N (N equal-width bins), '
             'or a duration string such as "1d" (days), "1w" (weeks), '
             '"1m" (months), "1y" (years). '
             'Ignored if --cumulative is used without --count.'
    )
    timeline_parser.add_argument(
        '-U',
        '--cumulative',
        action='store_true',
        default=False,
        help='plot cumulative event count. With --count: shows dual-axis '
             'histogram+cumulative. Without --count: shows raw cumulative '
             'over chronological time (no binning).'
    )
    timeline_parser.add_argument(
        '-b',
        '--backend',
        type=str,
        default='matplotlib',
        choices=['matplotlib', 'plotly', 'terminal'],
        help='plotting backend (default: %(default)s). '
             '"terminal" only supports count mode.'
    )
    timeline_parser.add_argument(
        '-o',
        '--out-file',
        type=str,
        default=None,
        metavar='FILE',
        help='output file (default: show on screen / open in browser). '
             'For matplotlib, the format is determined by the file extension '
             '(e.g., .png, .pdf, .svg). '
             'For plotly, the file should have a .html extension.'
    )


def _add_get_parser(subparser, parents):
    """Add the get subparser."""
    get_parser = subparser.add_parser(
        'get',
        parents=[parents['configfile_parser']],
        formatter_class=RichHelpFormatter,
        help='get the value of a specific event attribute'
    )
    get_parser.add_argument(
        'key',
        type=str,
        help='attribute name'
    )
    get_parser.add_argument(
        'eventid', nargs='?',
        help='event ID to get (if omitted, get values for all events)'
    ).completer = evid_completer
    get_parser.add_argument(
        'event_version',
        nargs='?',
        type=int,
        default=None,
        help='use this event version instead of the latest one'
    )


def _add_set_parser(subparser, parents):
    """Add the set subparser."""
    set_parser = subparser.add_parser(
        'set',
        parents=[parents['configfile_parser']],
        formatter_class=RichHelpFormatter,
        help='set the value of a specific event attribute'
    )
    set_parser.add_argument(
        'key',
        type=str,
        help='attribute name'
    )
    set_parser.add_argument(
        'value',
        type=str,
        help='attribute value'
    )
    set_parser.add_argument(
        'eventid',
        type=str,
        help='event ID to set'
    ).completer = evid_completer
    set_parser.add_argument(
        'event_version',
        nargs='?',
        type=int,
        default=None,
        help='use this event version instead of the latest one'
    )


def _add_run_parser(subparser, parents):
    """Add the run subparser."""
    run_parser = subparser.add_parser(
        'run',
        parents=[
            parents['configfile_parser'],
            parents['versions_parser'],
            parents['where_parser'],
            parents['sortby_parser'],
            parents['reverse_parser']
        ],
        formatter_class=RichHelpFormatter,
        help='run a user-defined command on each event'
    )
    run_parser.add_argument(
        'command',
        type=str,
        help='command to run. It can be any executable (e.g., shell script, '
             'Python script, etc.). All the columns of the events table will '
             'be available as environment variables (e.g., $evid, $time, etc.)'
    )
    run_parser.add_argument(
        'eventid', nargs='?',
        help='only run the command on this eventid'
    ).completer = evid_completer
    run_parser.epilog = (
        'Note: this command supports concurrent processes, all modifying the '
        'database. It is therefore safe to run multiple instances of this '
        'command at the same time.'
    )


def _add_daemon_parser(subparser, parents):
    """Add the daemon subparser tree."""
    daemon_parser = subparser.add_parser(
        'daemon',
        parents=[parents['configfile_parser']],
        formatter_class=RichHelpFormatter,
        help='manage the seiscat scheduled daemon'
    )
    daemon_subparser = daemon_parser.add_subparsers(
        dest='daemon_action',
        title='daemon commands'
    )
    daemon_subparser.metavar = '<daemon-command> [options]'

    # daemon run
    daemon_subparser.add_parser(
        'run',
        formatter_class=RichHelpFormatter,
        help='execute one daemon cycle (updatedb + optional fetch stages). '
             'Intended to be called by launchd or systemd, not interactively.'
    )

    # daemon install-service
    install_parser = daemon_subparser.add_parser(
        'install-service',
        formatter_class=RichHelpFormatter,
        help='generate and install a launchd plist (macOS) or systemd unit '
             'and timer (Linux) for the current user'
    )
    install_parser.add_argument(
        '--system',
        action='store_true',
        default=False,
        help='install as a system-wide service instead of a user service '
             '(requires root/sudo privileges)'
    )

    # daemon uninstall-service
    uninstall_parser = daemon_subparser.add_parser(
        'uninstall-service',
        formatter_class=RichHelpFormatter,
        help='remove the launchd plist or systemd unit/timer installed by '
             'install-service'
    )
    uninstall_parser.add_argument(
        '--system',
        action='store_true',
        default=False,
        help='uninstall the system-wide service instead of the user service'
    )

    # daemon status
    daemon_subparser.add_parser(
        'status',
        formatter_class=RichHelpFormatter,
        help='show the service status and last-run metadata'
    )


def _add_sampleconfig_parser(subparser):
    """Add the sampleconfig subparser."""
    subparser.add_parser(
        'sampleconfig',
        formatter_class=RichHelpFormatter,
        help='write a sample config file')


def _add_samplescript_parser(subparser):
    """Add the samplescript subparser."""
    subparser.add_parser(
        'samplescript',
        formatter_class=RichHelpFormatter,
        help='write a sample script file to be used with the "run" command'
    )


def _add_self_parser(subparser):
    """Add the self-management subparser tree."""
    self_parser = subparser.add_parser(
        'self',
        formatter_class=RichHelpFormatter,
        help='manage seiscat installation, updates, completion, and logo'
    )
    self_subparser = self_parser.add_subparsers(
        dest='self_action',
        title='self commands'
    )
    self_subparser.metavar = '<self-command> [options]'

    self_subparser.add_parser(
        'status',
        formatter_class=RichHelpFormatter,
        help='show self-management status'
    )

    update_parser = self_subparser.add_parser(
        'update',
        formatter_class=RichHelpFormatter,
        help='update seiscat (release by default)'
    )
    update_parser.add_argument(
        '--git',
        action='store_true',
        default=False,
        help='update/switch to latest git version instead of release track'
    )

    uninstall_parser = self_subparser.add_parser(
        'uninstall',
        formatter_class=RichHelpFormatter,
        help='uninstall seiscat from current environment/tool backend'
    )
    uninstall_parser.add_argument(
        '--yes',
        action='store_true',
        default=False,
        help='skip interactive confirmation'
    )

    completion_parser = self_subparser.add_parser(
        'completion',
        formatter_class=RichHelpFormatter,
        help='manage shell completion'
    )
    completion_subparser = completion_parser.add_subparsers(
        dest='self_completion_action',
        title='completion commands'
    )
    completion_subparser.metavar = '<completion-command> [options]'
    completion_subparser.add_parser(
        'status',
        formatter_class=RichHelpFormatter,
        help='show shell completion status'
    )
    completion_subparser.add_parser(
        'install',
        formatter_class=RichHelpFormatter,
        help='install/repair shell completion'
    )

    logo_parser = self_subparser.add_parser(
        'logo',
        formatter_class=RichHelpFormatter,
        help='print the seiscat logo 🐱'
    )
    logo_parser.add_argument(
        '--compact',
        action='store_true',
        default=False,
        help='print compact logo variant'
    )


def _add_main_arguments(parser):
    """Add main arguments."""
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=f"%(prog)s {get_versions()['version']}",
    )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            f'{SEISCAT_LOGO_SMALL}Keep a local seismic catalog.'
        ),
        formatter_class=SubcommandHelpFormatter,
        add_help=True
    )
    _add_main_arguments(parser)
    subparser = parser.add_subparsers(dest='action', title='commands')
    subparser.metavar = '<command> [options]'
    # Set parser class for subcommands (used for those added after this point)
    subparser._parser_class = CustomArgumentParser
    parents = _get_parent_parsers()
    _add_initdb_parser(subparser, parents)
    _add_updatedb_parser(subparser, parents)
    _add_editdb_parser(subparser, parents)
    _add_cropdb_parser(subparser, parents)
    _add_print_parser(subparser, parents)
    _add_export_parser(subparser, parents)
    _add_plot_parser(subparser, parents)
    _add_timeline_parser(subparser, parents)
    _add_get_parser(subparser, parents)
    _add_set_parser(subparser, parents)
    _add_fetchdata_parser(subparser, parents)
    _add_run_parser(subparser, parents)
    if platform.system().lower() != 'windows':
        _add_daemon_parser(subparser, parents)
    _add_sampleconfig_parser(subparser)
    _add_samplescript_parser(subparser)
    _add_self_parser(subparser)
    # Check if we're in completion mode before running argcomplete
    # This avoids unnecessary overhead when not doing shell completion
    if '_ARGCOMPLETE' in os.environ:
        argcomplete.autocomplete(parser)
    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        sys.exit(0)
    if args.action == 'self' and getattr(args, 'self_action', None) is None:
        parser.parse_args(['self', '--help'])
        sys.exit(0)
    if (
        args.action == 'self'
        and getattr(args, 'self_action', None) == 'completion'
        and getattr(args, 'self_completion_action', None) is None
    ):
        parser.parse_args(['self', 'completion', '--help'])
        sys.exit(0)
    if (
        args.action == 'daemon'
        and getattr(args, 'daemon_action', None) is None
    ):
        parser.parse_args(['daemon', '--help'])
        sys.exit(0)
    return args

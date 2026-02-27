# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Read an event catalog from any file format supported by ObsPy.

This module reads event files using obspy.read_events(), which supports
multiple formats including QuakeML, SC3ML, NLLOC, etc.

:copyright:
    2021-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from obspy import read_events


def read_catalog_from_obspy_events(config, filename=None):
    """
    Read a catalog from an event file using obspy.read_events().

    Uses ObsPy's format auto-detection for supported formats.

    :param config: configuration object
    :type config: dict
    :param filename: event filename (if None, uses args.fromfile[0])
    :type filename: str or None

    :return: an ObsPy catalog object
    :rtype: obspy.Catalog

    :raises FileNotFoundError: if filename does not exist
    :raises Exception: if file cannot be read by ObsPy
    """
    args = config['args']
    # Support both filename parameter and args.fromfile list
    event_filename = filename if filename is not None else args.fromfile[0]
    # First, try ObsPy's read_events with format auto-detection
    try:
        cat = read_events(event_filename)
        # Get format info for display
        format_info = 'unknown'
        if cat and cat.events:
            format_info = cat[0]._format  # pylint: disable=protected-access
        print(
            f'Successfully read {len(cat)} events using ObsPy '
            f'(format: {format_info})'
        )
        return cat
    except FileNotFoundError as e:
        # Re-raise FileNotFoundError as-is
        raise FileNotFoundError(
            f'Event file not found: {event_filename}'
        ) from e
    except Exception as e:
        # ObsPy could not read the file
        raise ValueError(
            f'ObsPy could not read event file:\n{e}'
        ) from e

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Download event details from FDSN web services and store them to local files.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
import warnings
from obspy.clients.fdsn.header import (
    FDSNNotImplementedException, FDSNNoDataException
)
from ..database.dbfunctions import read_events_from_db
from ..sources.fdsnws import open_fdsn_connection
from ..utils import ExceptionExit
from .event_waveforms_utils import get_event_layout_paths


def _get_events(client, evid):
    """
    Get events from FDSN client, falling back to no arrivals if not supported.

    :param client: FDSN client
    :param evid: event id
    :returns: obspy catalog
    :raises ValueError, FDSNNoDataException: if the request fails
    """
    try:
        return client.get_events(eventid=evid, includearrivals=True)
    except FDSNNotImplementedException:
        return client.get_events(eventid=evid)


def _fetch_event(client, evid, raw_evid):
    """
    Fetch a single event from the FDSN client, retrying with raw_evid on fail.

    Prints status messages. Returns None if all attempts fail.

    :param client: FDSN client
    :param evid: normalized event id
    :param raw_evid: raw (original) resource_id string, or None
    :returns: obspy catalog, or None on failure
    """
    try:
        return _get_events(client, evid)
    except (ValueError, FDSNNoDataException) as e:
        if not raw_evid or raw_evid == evid:
            print(
                f'Cannot fetch event details for {evid} '
                f'from server {client.base_url}: {e}'
            )
            return None
        first_error = e
    print(
        f'normalized evid failed ({first_error}), retrying with raw_evid...',
        end=' '
    )
    try:
        return _get_events(client, raw_evid)
    except (ValueError, FDSNNoDataException) as e2:
        print(
            f'Cannot fetch event details for {evid} '
            f'from server {client.base_url}: {e2}'
        )
        return None


def fetch_event_details(config):
    """
    Fetch event details from FDSN web services
    and store them to local files.

    :param config: config object
    """
    with ExceptionExit():
        events = read_events_from_db(config)
    with ExceptionExit(additional_msg='Error connecting to FDSN server'):
        client = open_fdsn_connection(config)
    event_dir = pathlib.Path(config['event_dir'])
    event_dir.mkdir(parents=True, exist_ok=True)
    overwrite_existing = config['args'].overwrite_existing
    for event in events:
        evid = event['evid']
        # .get() returns None if 'raw_evid' column doesn't exist
        raw_evid = event.get('raw_evid')
        print(f'{evid}:', end=' ')
        paths = get_event_layout_paths(config, evid)
        evid_dir = pathlib.Path(paths['evid_dir'])
        evid_dir.mkdir(parents=True, exist_ok=True)
        outfile = paths['event_xml_file']
        if not overwrite_existing and outfile.exists():
            print(f'{outfile} exists, skipping')
            continue
        fetched = _fetch_event(client, evid, raw_evid)
        if fetched is None:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            fetched.write(outfile, format='QUAKEML')
        print(f'event details saved to {outfile}')

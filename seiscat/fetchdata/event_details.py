# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Download event details from FDSN web services and store them to local files.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
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
        print(f'{evid}:', end=' ')
        evid_dir = pathlib.Path(event_dir / f'{evid}')
        evid_dir.mkdir(parents=True, exist_ok=True)
        outfile = evid_dir / f'{evid}.xml'
        if not overwrite_existing and outfile.exists():
            print(f'{outfile} exists, skipping')
            continue
        try:
            try:
                event = client.get_events(eventid=evid, includearrivals=True)
            except FDSNNotImplementedException:
                event = client.get_events(eventid=evid)
        except FDSNNoDataException:
            print(f'No data available for {evid}')
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            event.write(outfile, format='QUAKEML')
        print(f'event details saved to {outfile}')

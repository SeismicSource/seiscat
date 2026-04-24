# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fetch event waveforms from FDSN web services or from a local SDS archive.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
from .sds import get_sds_client, fetch_sds_waveforms
from .mass_downloader import mass_download_waveforms
from ..database.dbfunctions import read_events_from_db
from ..utils import ExceptionExit


def fetch_event_waveforms(config):
    """
    Fetch event waveforms from FDSN web services
    or from a local SDS archive.

    :param config: config object
    """
    with ExceptionExit():
        events = read_events_from_db(config)
        event_dir = pathlib.Path(config['event_dir'])
        event_dir.mkdir(parents=True, exist_ok=True)
        args = config['args']
        n_events_processed = len(events)
        n_events_downloaded = 0
        n_stations_downloaded = 0
        if args.sds:
            sds_client = get_sds_client(args.sds)
            for event in events:
                n_stations = fetch_sds_waveforms(config, event, sds_client)
                n_stations_downloaded += n_stations
                if n_stations > 0:
                    n_events_downloaded += 1
        else:
            for event in events:
                n_stations = mass_download_waveforms(config, event)
                n_stations_downloaded += n_stations
                if n_stations > 0:
                    n_events_downloaded += 1
        print(
            f'\nfetchdata summary: {n_events_downloaded}/{n_events_processed} '
            f'events with downloaded waveforms, '
            f'{n_stations_downloaded} stations downloaded'
        )

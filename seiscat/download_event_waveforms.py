# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Uses ObsPy mass downloader to download event waveforms from FDSN web services.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
from obspy.clients.fdsn.mass_downloader import CircularDomain, \
    Restrictions, MassDownloader
from .db import read_events_from_db
from .utils import ExceptionExit


def _download_waveforms(config, event):
    """
    Download waveforms for a single event using ObsPy mass downloader.

    :param config: config object
    :param event: event object
    """
    evid = event['evid']
    latitude = event['lat']
    longitude = event['lon']
    origin_time = event['time']
    providers = config['fdsn_providers']
    station_radius_min = config['station_radius_min']
    station_radius_max = config['station_radius_max']
    seconds_before = config['seconds_before_origin']
    seconds_after = config['seconds_after_origin']
    duration_min = config['duration_min']
    interstation_distance_min = config['interstation_distance_min']
    channel_priorities = config['channel_priorities']
    location_priorities = config['location_priorities']

    event_dir = pathlib.Path(config['event_dir'])
    evid_dir = event_dir / f'{evid}'
    waveform_dir = pathlib.Path(evid_dir / config['waveform_dir'])
    waveform_dir.mkdir(parents=True, exist_ok=True)
    station_dir = pathlib.Path(evid_dir / config['station_dir'])
    station_dir.mkdir(parents=True, exist_ok=True)

    print(f'{evid}: downloading waveforms and station metadata\n')

    domain = CircularDomain(
        latitude=latitude, longitude=longitude,
        minradius=station_radius_min, maxradius=station_radius_max
    )
    restrictions = {
        'starttime': origin_time - seconds_before,
        'endtime': origin_time + seconds_after,
        'reject_channels_with_gaps': False,
        'minimum_length': duration_min,
        'minimum_interstation_distance_in_m': interstation_distance_min * 1e3,
    }
    if channel_priorities:
        restrictions['channel_priorities'] = channel_priorities
    if location_priorities:
        restrictions['location_priorities'] = location_priorities
    restrictions = Restrictions(**restrictions)
    with ExceptionExit():
        mdl = MassDownloader(providers=providers)
        mdl.download(
            domain, restrictions,
            mseed_storage=str(waveform_dir),
            stationxml_storage=str(station_dir)
        )
        print(
            f'\n{evid}: waveforms and station metadata saved to '
            f'{evid_dir}\n\n'
        )


def download_event_waveforms(config):
    """
    Uses ObsPy mass downloader to download event waveforms from FDSN
    web services.

    :param config: config object
    """
    with ExceptionExit():
        events = read_events_from_db(config)
    event_dir = pathlib.Path(config['event_dir'])
    event_dir.mkdir(parents=True, exist_ok=True)
    for event in events:
        _download_waveforms(config, event)

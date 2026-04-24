# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fetch event waveforms from a local SDS archive.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
import re
import shutil
from obspy.clients.filesystem.sds import Client
from .event_waveforms_utils import (
    prefer_high_sampling_rate,
    check_station,
    get_picked_station_codes,
    get_event_layout_paths,
    get_event_xml_file,
    bundle_waveforms_to_mseed,
)


def get_sds_client(sds_root):
    """
    Get an SDS client.

    :param sds_root: path to SDS archive
    :type sds_root: str

    :return: SDS client
    :rtype: obspy.clients.filesystem.sds.Client
    """
    client = Client(sds_root)
    # Ensure the archive has at least one NSLC entry before accepting it.
    if client.get_all_nslc():
        return client
    else:
        raise FileNotFoundError(
            f'No SDS archive found in {sds_root}')


def _check_channel(channel, channel_codes):
    """
    Check if a channel matches the specified channel codes.
    The channel codes can contain wildcards:
    - '*' matches any number of characters
    - '?' matches a single character

    :param channel: channel code
    :type channel: str
    :param channel_codes: string with channel codes separated by commas
    :type channel_codes: str

    :return: True if the channel is in the list of channel priorities
    :rtype: bool
    """
    # Escape dots, replace `?` with `.`, replace `*` with `.*`,
    # and split by comma
    regex_parts = [
        code.replace('.', r'\.')   # Escape dots if any
            .replace('?', '.')     # Single-character wildcard
            .replace('*', '.*')    # Multi-character wildcard
        for code in channel_codes.split(',')
    ]
    # Join with `|` to create an OR pattern
    regex = f"^({'|'.join(regex_parts)})$"
    return bool(re.match(regex, channel))


def fetch_sds_waveforms(config, event, client):
    """
    Fetch event waveforms from a local SDS archive.

    :param config: config object
    :type config: dict
    :param event: an event dictionary
    :type event: dict
    :param client: SDS client
    :type client: obspy.clients.filesystem.sds.Client
    :returns: number of stations downloaded for this event
    """
    evid = event['evid']
    paths = get_event_layout_paths(config, evid)
    evid_dir = paths['evid_dir']
    waveform_dir = pathlib.Path(paths['waveform_dir'])
    waveform_dir.mkdir(parents=True, exist_ok=True)
    seconds_before = config['seconds_before_origin']
    seconds_after = config['seconds_after_origin']
    t0 = event['time'] - seconds_before
    t1 = event['time'] + seconds_after
    channel_codes = config['channel_codes']
    station_codes = config['station_codes']
    picked_stations_only = config['picked_stations_only']
    # Build set of allowed stations from picks, if requested
    picked_stations = None
    if picked_stations_only:
        picked_stations = get_picked_station_codes(evid_dir, evid)
        if picked_stations is None:
            event_xml = get_event_xml_file(evid_dir, evid)
            if event_xml is None:
                event_xml = evid_dir / f'{evid}.xml'
            print(
                f'{evid}: picked_stations_only is True but no event QuakeML '
                f'file found at {event_xml}. '
                'Ignoring pick-based station selection.'
            )
        elif not picked_stations:
            print(
                f'{evid}: No P/S picks found in the event QuakeML file. '
                'No waveforms will be downloaded.'
            )
            return 0
        else:
            if station_codes:
                picked_stations = {
                    sta for sta in picked_stations
                    if check_station(sta, station_codes)
                }
                if not picked_stations:
                    print(
                        f'{evid}: No picked stations match station_codes '
                        f'"{station_codes}". No waveforms will be downloaded.'
                    )
                    return 0
    print(f'Fetching waveforms for event: {evid}')
    downloaded_stations = set()
    all_nslc = client.get_all_nslc()
    for nslc in all_nslc:
        net, sta, loc, chan = nslc
        if channel_codes and not _check_channel(chan, channel_codes):
            continue
        if (
            station_codes
            and picked_stations is None
            and not check_station(sta, station_codes)
        ):
            # Only station_codes filter, no picks filter
            continue
        if picked_stations is not None and sta not in picked_stations:
            continue
        st = client.get_waveforms(net, sta, loc, chan, t0, t1)
        outfile = waveform_dir / f'{net}.{sta}.{loc}.{chan}.mseed'
        st.write(outfile, format='MSEED')
        downloaded_stations.add((net, sta))
        print(f'  {outfile} written')
    if config['prefer_high_sampling_rate']:
        prefer_high_sampling_rate(waveform_dir)
    if paths['layout'] == 'event_files':
        if bundle_waveforms_to_mseed(waveform_dir, paths['waveform_file']):
            print(f'  {paths["waveform_file"]} written')
        shutil.rmtree(waveform_dir, ignore_errors=True)
    print()
    return len(downloaded_stations)

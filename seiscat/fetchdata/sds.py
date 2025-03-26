# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fetch event waveforms from a local SDS archive.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
import re
from obspy.clients.filesystem.sds import Client
from .event_waveforms_utils import prefer_high_sampling_rate


def get_sds_client(sds_root):
    """
    Get an SDS client.

    :param sds_root: path to SDS archive
    :type sds_root: str

    :return: SDS client
    :rtype: obspy.clients.filesystem.sds.Client
    """
    client = Client(sds_root)
    all_nslc = client.get_all_nslc()
    if not all_nslc:
        raise FileNotFoundError(
            f'No SDS archive found in {sds_root}')
    return client


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
    """
    evid = event['evid']
    event_dir = pathlib.Path(config['event_dir'])
    evid_dir = event_dir / f'{evid}'
    waveform_dir = pathlib.Path(evid_dir / config['waveform_dir'])
    waveform_dir.mkdir(parents=True, exist_ok=True)
    seconds_before = config['seconds_before_origin']
    seconds_after = config['seconds_after_origin']
    t0 = event['time'] - seconds_before
    t1 = event['time'] + seconds_after
    channel_codes = config['channel_codes']
    print(f'Fetching waveforms for event: {evid}')
    all_nslc = client.get_all_nslc()
    for nslc in all_nslc:
        net, sta, loc, chan = nslc
        if not _check_channel(chan, channel_codes):
            continue
        st = client.get_waveforms(net, sta, loc, chan, t0, t1)
        outfile = waveform_dir / f'{net}.{sta}.{loc}.{chan}.mseed'
        st.write(outfile, format='MSEED')
        print(f'  {outfile} written')
    if config['prefer_high_sampling_rate']:
        prefer_high_sampling_rate(waveform_dir)
    print()

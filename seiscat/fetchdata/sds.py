# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fetch event waveforms from a local SDS archive.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
import re
from obspy.clients.filesystem.sds import Client


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


def _check_channel(channel, channel_priorities):
    """
    Check if a channel is in the list of channel priorities.

    :param channel: channel code
    :type channel: str
    :param channel_priorities: list of channel codes
    :type channel_priorities: list

    :return: True if the channel is in the list of channel priorities
    :rtype: bool
    """
    for priority in channel_priorities:
        # Convert wildcard pattern to regex pattern
        regex_pattern = re.escape(priority)\
            .replace(r'\*', '.*').replace(r'\?', '.')
        # Handle character sets like [ZNE]
        regex_pattern = re.sub(r'\\\[([^\\\]]+)\\\]', r'[\1]', regex_pattern)
        if re.fullmatch(regex_pattern, channel):
            return True
    return False


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
    event_dir = pathlib.Path(config['event_dir'], event['evid'], 'waveforms')
    event_dir.mkdir(parents=True, exist_ok=True)
    seconds_before = config['seconds_before_origin']
    seconds_after = config['seconds_after_origin']
    t0 = event['time'] - seconds_before
    t1 = event['time'] + seconds_after
    channel_priorities = config['channel_priorities']
    print(f'Fetching waveforms for event: {event["evid"]}')
    all_nslc = client.get_all_nslc()
    for nslc in all_nslc:
        if not _check_channel(nslc[-1], channel_priorities):
            continue
        net, sta, loc, chan = nslc
        st = client.get_waveforms(net, sta, loc, chan, t0, t1)
        outfile = event_dir / f'{net}.{sta}.{loc}.{chan}.mseed'
        st.write(outfile, format='MSEED')
        print(f'  {outfile} written')
    print()

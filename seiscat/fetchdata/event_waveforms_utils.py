# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Uses ObsPy mass downloader to download event waveforms from FDSN web services.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import re
import pathlib
from functools import cmp_to_key


def _sort_by_band_code(file_1, file_2):
    """
    Sort two miniSEED files by band code, in decreasing order of sampling rate.

    :param file_1: first miniSEED file as pathlib.Path object
    :type file_1: pathlib.Path
    :param file_2: second miniSEED file as pathlib.Path object
    :type file_2: pathlib.Path
    :return: -1 if file_1 has a lower band code than file_2,
             1 if file_1 has a higher band code than file_2,
             0 if they have the same band code
    """
    seed_id_1 = file_1.name.split('__')[0]
    seed_id_2 = file_2.name.split('__')[0]
    # band codes in decreasing order of sampling rate, according to
    # the SEED manual
    sorted_band_codes = 'FGDCESHBMLVURPTQAO'
    band_code_1 = seed_id_1.split('.')[-1][0]
    band_code_2 = seed_id_2.split('.')[-1][0]
    idx_1 = sorted_band_codes.index(band_code_1)
    idx_2 = sorted_band_codes.index(band_code_2)
    if idx_1 == idx_2:
        return 0
    if idx_1 < idx_2:
        return -1
    if idx_1 > idx_2:
        return 1


def prefer_high_sampling_rate(waveform_dir, logger=None):
    """
    Remove low sampling rate files from the waveform directory."

    :param waveform_dir: path to the waveform directory
    :type waveform_dir: str
    :param logger: logger object
    :type logger: logging.Logger
    """
    seed_ids = set()
    for station_file in waveform_dir.glob('*.mseed'):
        _sid = str(station_file.name).split('__', maxsplit=1)[0]
        _sid = list(_sid)
        _sid[-3] = '?'
        _sid = ''.join(_sid)
        seed_ids.add(_sid)
    for sid in seed_ids:
        filelist = sorted(
            list(waveform_dir.glob(f'{sid}*')),
            key=cmp_to_key(_sort_by_band_code)
        )
        if len(filelist) < 2:
            continue
        for file in filelist[1:]:
            _info_msg = f'{filelist[0].name} preferred over {file.name}'
            if logger:
                logger.info(_info_msg)
            else:
                print(_info_msg)
            file.unlink()


def check_station(station, station_codes):
    """
    Check if a station matches the specified station codes.
    The station codes can contain wildcards:
    - '*' matches any number of characters
    - '?' matches a single character

    :param station: station code
    :type station: str
    :param station_codes: string with station codes separated by commas
    :type station_codes: str

    :return: True if the station matches one of the specified patterns
    :rtype: bool
    """
    regex_parts = [
        code.strip()
            .replace('.', r'\.')   # Escape dots if any
            .replace('?', '.')     # Single-character wildcard
            .replace('*', '.*')    # Multi-character wildcard
        for code in station_codes.split(',')
    ]
    regex = f"^({'|'.join(regex_parts)})$"
    return bool(re.match(regex, station))


def get_picked_station_codes(evid_dir, evid):
    """
    Read the event QuakeML file and return the set of station codes
    that have at least one P or S-wave pick.

    :param evid_dir: path to the event directory
    :type evid_dir: pathlib.Path
    :param evid: event ID
    :type evid: str

    :return: set of station codes with picks, or None if the file is not found
    :rtype: set or None
    """
    import warnings
    from obspy import read_events
    xml_file = pathlib.Path(evid_dir) / f'{evid}.xml'
    if not xml_file.exists():
        return None
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        catalog = read_events(str(xml_file))
    station_codes = set()
    for event in catalog:
        for pick in event.picks:
            phase = None
            # Try to get phase hint from associated arrivals
            for origin in event.origins:
                for arrival in origin.arrivals:
                    if arrival.pick_id == pick.resource_id:
                        phase = arrival.phase
                        break
                if phase is not None:
                    break
            # Fall back to pick.phase_hint if no arrival found
            if phase is None:
                phase = pick.phase_hint
            if phase is not None and phase[0].upper() in ('P', 'S'):
                if pick.waveform_id and pick.waveform_id.station_code:
                    station_codes.add(pick.waveform_id.station_code)
    return station_codes

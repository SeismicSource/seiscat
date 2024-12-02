# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fetch event waveforms from FDSN web services or from a local SDS archive.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
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
    for event in events:
        mass_download_waveforms(config, event)

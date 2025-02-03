# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Get or set the value of a specific event attribute

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .dbfunctions import read_fields_and_rows_from_db, update_event_in_db
from ..utils import err_exit, ExceptionExit


def seiscat_get(config):
    """
    Get the value of a specific event attribute
    """
    args = config['args']
    field_list = [args.key]
    with ExceptionExit():
        _, rows = read_fields_and_rows_from_db(
            config, eventid=args.eventid, version=args.version,
            field_list=field_list)
    if not rows:
        err_exit('Event not found')
    print(rows[0][0])


def seiscat_set(config):
    """
    Set the value of a specific event attribute
    """
    args = config['args']
    field_list = ['ver', args.key]
    with ExceptionExit():
        fields, rows = read_fields_and_rows_from_db(
            config, eventid=args.eventid, version=args.version,
            field_list=field_list)
    if not rows:
        err_exit('Event not found')
    version_idx = fields.index('ver')
    version = rows[0][version_idx]
    update_event_in_db(
        config, args.eventid, version, args.key, args.value)

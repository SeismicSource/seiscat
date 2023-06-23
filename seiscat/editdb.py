# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Edit functions for seiscat.

:copyright:
    2022-2023 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .utils import err_exit
from .db import (
    read_fields_and_rows_from_db, replicate_event_in_db,
    delete_event_from_db, update_event_in_db)


def _are_you_sure(msg):
    """
    Ask user if she is sure to proceed.

    :param msg: message to print
    """
    print(msg)
    answer = input('Are you sure? [y/N] ')
    if answer.lower() != 'y':
        err_exit('Aborted')


def _parse_set_arg(arg):
    """
    Parse "--set" argument.

    :param arg: argument string
    :return: key, value
    """
    if '=' not in arg:
        err_exit(
            f'Invalid argument "{arg}" for "--set". '
            'Argument must be in the form "key=value"')
    key, val = arg.split('=')
    return key, val


def editdb(config):
    """
    Edit database.

    :param config: config object
    """
    args = config['args']
    eventid = args.eventid[0]
    version = args.version
    fields, rows = read_fields_and_rows_from_db(config, eventid, version)
    if not rows:
        if version:
            msg = f'Event {eventid} version {version} not found in database'
        else:
            msg = f'Event {eventid} not found in database'
        err_exit(msg)
    if len(rows) > 1:
        err_exit(
            f'Event {eventid} has {len(rows)} versions, '
            'please specify version with "--version"')
    if args.replicate:
        replicate_event_in_db(config, eventid)
    elif args.delete:
        version = rows[0][fields.index('ver')]
        if not args.force:
            _are_you_sure(
                f'Delete event {eventid} version {version} from database?')
        delete_event_from_db(config, eventid, version)
    elif args.set:
        version = rows[0][fields.index('ver')]
        if not args.force:
            _are_you_sure(
                f'Update event {eventid} version {version} in database?')
        key_values = [_parse_set_arg(arg) for arg in args.set]
        for key, val in key_values:
            update_event_in_db(config, eventid, version, key, val)
    else:
        err_exit('No action specified. See "seiscat editdb -h" for help')

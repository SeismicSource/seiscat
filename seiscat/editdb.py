# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Edit functions for seiscat.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .utils import err_exit
from .db import (
    read_fields_and_rows_from_db, replicate_event_in_db,
    delete_event_from_db, update_event_in_db, increment_event_in_db)


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


def _replicate(config, fields, rows):
    """
    Replicate event in database.

    :param config: config object
    :param fields: list of fields
    :param rows: list of rows
    """
    for row in rows:
        eventid = row[fields.index('evid')]
        version = row[fields.index('ver')]
        replicate_event_in_db(config, eventid, version)


def _delete(config, fields, rows, eventid, version, args):
    """
    Delete event from database.

    :param config: config object
    :param fields: list of fields
    :param rows: list of rows
    :param eventid: event ID
    :param version: event version
    :param args: parsed arguments
    """
    if eventid:
        version = rows[0][fields.index('ver')]
        if not args.force:
            _are_you_sure(
                f'Delete event {eventid} version {version} from database?')
    elif version and not args.force:
        _are_you_sure(
            f'Delete ALL events of version {version} from database?')
    elif not version and not args.force:
        _are_you_sure('Delete ALL events from database?')
    delete_event_from_db(config, eventid, version)


def _set(config, fields, rows, key_values, args):
    """
    Set key-value pairs in database.

    :param config: config object
    :param fields: list of fields
    :param rows: list of rows
    :param key_values: list of key-value pairs
    :param args: parsed arguments
    """
    if len(rows) == 1 and not args.force:
        eventid = rows[0][fields.index('evid')]
        version = rows[0][fields.index('ver')]
        _are_you_sure(
            f'Update event {eventid} version {version} in database?')
    elif not args.force:
        _are_you_sure(
            f'Update {len(rows)} events in database?')
    for row in rows:
        eventid = row[fields.index('evid')]
        version = row[fields.index('ver')]
        key_values = [_parse_set_arg(arg) for arg in args.set]
        for key, val in key_values:
            update_event_in_db(config, eventid, version, key, val)


def _increment(config, fields, rows, key_values, args):
    """
    Increment key-value pairs in database.

    :param config: config object
    :param fields: list of fields
    :param rows: list of rows
    :param key_values: list of key-value pairs
    :param args: parsed arguments
    """
    if len(rows) == 1 and not args.force:
        eventid = rows[0][fields.index('evid')]
        version = rows[0][fields.index('ver')]
        _are_you_sure(
            f'Update event {eventid} version {version} in database?')
    elif not args.force:
        _are_you_sure(
            f'Update {len(rows)} events in database?')
    for row in rows:
        eventid = row[fields.index('evid')]
        version = row[fields.index('ver')]
        key_values = [_parse_set_arg(arg) for arg in args.increment]
        for key, val in key_values:
            increment_event_in_db(config, eventid, version, key, val)


def editdb(config):
    """
    Edit database.

    :param config: config object
    """
    args = config['args']
    eventid = args.eventid[0]
    version = args.version
    if eventid == 'ALL':
        eventid = None
    fields, rows = read_fields_and_rows_from_db(config, eventid, version)
    if not rows:
        if eventid and version:
            msg = f'Event {eventid} version {version} not found in database'
        elif eventid:
            msg = f'Event {eventid} not found in database'
        else:
            msg = 'No events found in database'
        err_exit(msg)
    if eventid and len(rows) > 1:
        err_exit(
            f'Event {eventid} has {len(rows)} versions, '
            'please specify version with "--version"')
    if args.replicate:
        _replicate(config, fields, rows)
    elif args.delete:
        _delete(config, fields, rows, eventid, version, args)
    elif args.set:
        _set(config, fields, rows, args.set, args)
    elif args.increment:
        _increment(config, fields, rows, args.increment, args)
    else:
        err_exit('No action specified. See "seiscat editdb -h" for help')

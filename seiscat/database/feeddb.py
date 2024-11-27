# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Feed the database with events from FDSN web services.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .dbfunctions import check_db_exists, write_catalog_to_db
from ..sources.fdsnws import open_fdsn_connection, query_events
from ..utils import ExceptionExit


def feeddb(config, initdb):
    """
    Feed the database with events from FDSN web services.

    :param config: config object
    :param initdb: if True, create new database file
    """
    with ExceptionExit():
        check_db_exists(config, initdb)
    with ExceptionExit(additional_msg='Error connecting to FDSN server'):
        client = open_fdsn_connection(config)
    with ExceptionExit(additional_msg='Error querying FDSN server'):
        cat = query_events(client, config, first_query=initdb)
    with ExceptionExit(additional_msg='Error writing to database'):
        write_catalog_to_db(cat, config, initdb)

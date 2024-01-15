# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Download and store events.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .db import check_db_exists, write_catalog_to_db
from .fdsnws import open_fdsn_connection, query_events
from .utils import err_exit


def download_and_store(config, initdb):
    """
    Download events and store them in the database.

    :param config: config object
    :param initdb: if True, create new database file
    """
    check_db_exists(config, initdb)
    try:
        client = open_fdsn_connection(config)
    except Exception as e:
        err_exit(e)
    cat = query_events(client, config, first_query=initdb)
    write_catalog_to_db(cat, config, initdb)

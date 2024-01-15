# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot events on a map.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""


def plot_catalog_map(config):
    """
    Plot the catalog map.

    :param config: config object
    """
    from .plot_map_cartopy import plot_catalog_map_with_cartopy
    plot_catalog_map_with_cartopy(config)

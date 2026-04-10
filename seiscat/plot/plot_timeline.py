# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Plot catalog timeline — backend dispatcher.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from ..utils import err_exit
from ..database.dbfunctions import read_events_from_db
from .plot_utils import get_matplotlib_colormap


def plot_catalog_timeline(config):
    """
    Plot the catalog timeline.

    Reads events from the database and dispatches to the appropriate backend
    (matplotlib, plotly, or terminal) as specified by ``args.backend``.

    :param config: config object
    """
    args = config['args']
    if not args.count and not getattr(args, 'cumulative', False) and \
            args.backend != 'terminal':
        # Validate the colormap before loading events or importing a backend
        # so invalid names fail immediately for scatter plots.
        get_matplotlib_colormap(getattr(args, 'colormap', None))
    try:
        events = read_events_from_db(config)
    except (FileNotFoundError, ValueError) as msg:
        err_exit(msg)

    # pylint: disable=import-outside-toplevel
    if args.backend == 'matplotlib':
        from .plot_timeline_matplotlib import plot_catalog_timeline_matplotlib
        plot_catalog_timeline_matplotlib(events, config)
        return
    if args.backend == 'plotly':
        from .plot_timeline_plotly import plot_catalog_timeline_plotly
        plot_catalog_timeline_plotly(events, config)
        return
    if args.backend == 'terminal':
        from .plot_timeline_terminal import plot_catalog_timeline_terminal
        plot_catalog_timeline_terminal(events, config)
        return
    err_exit(f'Invalid backend "{args.backend}"')

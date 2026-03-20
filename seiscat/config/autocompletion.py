# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Autocompletion helpers for CLI arguments.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
# Curated fallback names used when Matplotlib cannot be imported at
# completion time. Keep only canonical names here (no _r variants).
_FALLBACK_MATPLOTLIB_COLORMAP_BASE_NAMES = (
    'Accent', 'Blues', 'BrBG', 'BuGn', 'BuPu', 'CMRmap', 'Dark2', 'GnBu',
    'Grays', 'Greens', 'Greys', 'OrRd', 'Oranges', 'PRGn', 'Paired',
    'Pastel1', 'Pastel2', 'PiYG', 'PuBu', 'PuBuGn', 'PuOr', 'PuRd',
    'Purples', 'RdBu', 'RdGy', 'RdPu', 'RdYlBu', 'RdYlGn', 'Reds', 'Set1',
    'Set2', 'Set3', 'Spectral', 'Wistia', 'YlGn', 'YlGnBu', 'YlOrBr',
    'YlOrRd', 'afmhot', 'autumn', 'berlin', 'binary', 'bone', 'brg',
    'bwr', 'cividis', 'cool', 'coolwarm', 'copper', 'cubehelix', 'flag',
    'gist_earth', 'gist_gray', 'gist_grey', 'gist_heat', 'gist_ncar',
    'gist_rainbow', 'gist_stern', 'gist_yarg', 'gist_yerg', 'gnuplot',
    'gnuplot2', 'gray', 'grey', 'hot', 'hsv', 'inferno', 'jet', 'magma',
    'managua', 'nipy_spectral', 'ocean', 'pink', 'plasma', 'prism',
    'rainbow', 'seismic', 'spring', 'summer', 'tab10', 'tab20', 'tab20b',
    'tab20c', 'terrain', 'turbo', 'twilight', 'twilight_shifted',
    'vanimo', 'viridis', 'winter'
)
# Full fallback completion set: base names plus generated reversed variants.
_FALLBACK_MATPLOTLIB_COLORMAPS = tuple(sorted(
    set(_FALLBACK_MATPLOTLIB_COLORMAP_BASE_NAMES)
    | {f'{name}_r' for name in _FALLBACK_MATPLOTLIB_COLORMAP_BASE_NAMES}
))


def _get_db_cursor(configfile):
    """
    Get a cursor to the database.

    :param configfile: path to config file
    :return: cursor to the database
    """
    try:
        fp = open(configfile, 'r', encoding='utf-8')
    except FileNotFoundError:
        return None
    try:
        db_file = [
            line.split('=')[1].strip() for line in fp
            if line.startswith('db_file')][0]
    except IndexError:
        db_file = None
    db_files_to_try = (
        [db_file]
        if db_file is not None
        else ['seiscat_db.sqlite', 'seiscat.sqlite']
    )
    for db_file in db_files_to_try:
        try:
            open(db_file, 'r', encoding='utf-8')
            break
        except FileNotFoundError:
            continue
    else:
        return None
    # pylint: disable=import-outside-toplevel
    import sqlite3  # lazy import to speed up startup time
    conn = sqlite3.connect(db_file)
    return conn.cursor()


def evid_completer(prefix, parsed_args, **_kwargs):
    """
    Completer for event IDs.

    :param prefix: prefix to complete
    :param parsed_args: parsed arguments
    :param kwargs: keyword arguments
    :return: list of event IDs
    """
    if evid_completer.db_cursor is None:
        evid_completer.db_cursor = _get_db_cursor(parsed_args.configfile)
    if evid_completer.db_cursor is None:
        return []
    # Count matching evids first to avoid overwhelming completion
    evid_completer.db_cursor.execute(
        'SELECT COUNT(*) FROM events WHERE evid LIKE ?', (f'{prefix}%',)
    )
    count = evid_completer.db_cursor.fetchone()[0]
    max_completions = 100
    if count > max_completions:
        return [
            f'[Too many events ({count}) for autocompletion'
            '\nUse exact EVID or --where to filter]'
        ]
    evid_completer.db_cursor.execute(
        'SELECT evid FROM events WHERE evid LIKE ?', (f'{prefix}%',)
    )
    return [row[0] for row in evid_completer.db_cursor.fetchall()]


evid_completer.db_cursor = None


def sortby_completer(prefix, parsed_args, **_kwargs):
    """
    Completer for sortby field names.

    :param prefix: prefix to complete
    :param parsed_args: parsed arguments
    :param kwargs: keyword arguments
    :return: list of field names
    """
    if sortby_completer.db_cursor is None:
        sortby_completer.db_cursor = _get_db_cursor(parsed_args.configfile)
    if sortby_completer.db_cursor is None:
        return []
    # Get all field names from the events table
    try:
        sortby_completer.db_cursor.execute('PRAGMA table_info(events)')
        # Field names are in the second column (index 1)
        all_fields = [row[1] for row in sortby_completer.db_cursor.fetchall()]
        # Filter by prefix
        return [field for field in all_fields if field.startswith(prefix)]
    except Exception:  # pylint: disable=broad-except
        return []


sortby_completer.db_cursor = None


def _get_matplotlib_colormap_names():
    """Return the exhaustive Matplotlib colormap registry when available."""
    try:
        from matplotlib import colormaps  # lazy import to keep startup fast
        return sorted(colormaps.keys())
    except Exception:  # pylint: disable=broad-except
        return list(_FALLBACK_MATPLOTLIB_COLORMAPS)


def colormap_completer(prefix, _parsed_args, **_kwargs):
    """Completer for Matplotlib colormap names."""
    prefix_lower = prefix.lower()
    return [
        name for name in _get_matplotlib_colormap_names()
        if name.lower().startswith(prefix_lower)
    ]

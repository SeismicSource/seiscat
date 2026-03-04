"""Sphinx configuration file."""
# pylint: disable=wrong-import-position,invalid-name

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.join(os.path.abspath('..'), 'seiscat'))
from seiscat._version import get_versions  # NOQA
__version__ = get_versions()['version']
__release_date__ = get_versions()['date']

# -- Project information -----------------------------------------------------

project = 'SeisCat'
copyright = '2022-2026, Claudio Satriano'  # pylint: disable=redefined-builtin
author = 'Claudio Satriano'

# The full version, including alpha/beta/rc tags.
release = __version__
# The short X.Y version.
version = release.split('-')[0]

# Release date in the format "Month DD, YYYY"
release_date = datetime.strptime(
    __release_date__, '%Y-%m-%dT%H:%M:%S%z'
).strftime('%b %d, %Y')
copyright_with_email = 'Claudio Satriano satriano@ipgp.fr'
release_date_line = f'.. |release date| replace:: {release_date}'
copyright_line = f'.. |copyright| replace:: {copyright_with_email}'
rst_epilog = f'\n{release_date_line}\n{copyright_line}'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx_mdinclude',
]
autodoc_mock_imports = [
    'matplotlib',
    'mpl_toolkits',
    'numpy',
    'obspy',
    'cartopy',
    'six',
    'argcomplete',
    'folium',
    'branca',
    'plotly',
    'pyproj',
    'shapefile',
    'shapely',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_logo = '_static/SeisCat_logo.svg'
html_static_path = ['_static']


# -- Custom functions for SeisCat ---------------------------------------------
def write_configfile(app):
    """Write configuration file documentation page."""
    # pylint: disable=unused-argument
    with open('configuration_file.rst', 'w', encoding='utf-8') as fp:
        fp.write('''.. _configuration_file:

##################
Configuration File
##################

Configuration file (default name: ``seiscat.conf``) is a plain text file
with keys and values in the form ``key = value``.
Comment lines start with ``#``.

Here is the default config file::

''')
        configspec = os.path.join(
            '..', 'seiscat', 'config', 'configspec.conf')
        for line in open(configspec, encoding='utf-8'):
            if '=' in line and line[0] != '#':
                key, val = line.split(' = ')
                val = val.split('default=')[1]
                # remove the word "list" from val
                val = val.replace('list', '')
                # remove single quotes and parentheses from val
                val = val.replace("'", '').replace('(', '').replace(')', '')
                line = f'{key} = {val}'
            fp.write(f'  {line}')


def setup(app):
    """Add custom functions to Sphinx."""
    app.connect('builder-inited', write_configfile)

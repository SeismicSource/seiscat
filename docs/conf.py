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
copyright = '2022-2024, Claudio Satriano'  # pylint: disable=redefined-builtin
author = 'Claudio Satriano'

# The full version, including alpha/beta/rc tags.
release = __version__
# The short X.Y version.
version = release.split('-')[0]

# Release date in the format "Month DD, YYYY"
release_date = datetime.strptime(
    __release_date__, '%Y-%m-%dT%H:%M:%S%z'
).strftime('%b %d, %Y')
rst_epilog = f'\n.. |release date| replace:: {release_date}'


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

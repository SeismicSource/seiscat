SeisCat
=======

Keep a local seismic catalog.

:Copyright: 2022-2026 |copyright|
:Release: |release|
:Date:    |release date|
:Project Page: `GitHub`_

Overview
--------

SeisCat is a command-line tool to build, maintain, and query a local seismic
catalog.

It builds and updates the catalog from FDSNWS event web services or local
event files. Input formats include CSV and any format handled by ObsPy
(QuakeML, SC3ML, NLLOC, etc.). The catalog is stored in a SQLite
single-file database and can be used as a basis for further analysis.

SeisCat also provides tools to plot and export the catalog, fetch waveforms
and station metadata for catalog events, and run user-defined scripts on those
events.


.. toctree::
   :hidden:

   self

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   getting_started
   configuration_file
   commands
   changelog
   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _GitHub: https://github.com/seismicsource/seiscat

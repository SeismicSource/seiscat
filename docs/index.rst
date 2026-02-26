SeisCat
=======

Keep a local seismic catalog.

:Copyright: 2022-2026 Claudio Satriano satriano@ipgp.fr
:Release: |release|
:Date:    |release date|

Overview
--------

SeisCat is a command line tool to keep a local seismic catalog.
The local catalog can be used as a basis for further analyses.

The seismic catalog is built and updated by querying a FDSNWS event webservice
or from a local event file. Supported formats include CSV and any format
supported by ObsPy (QuakeML, SC3ML, NLLOC, etc.).
More ways of feeding the catalog will be added in the future.

The local catalog is stored in a SQLite database (single file database).


.. toctree::
   :hidden:

   self

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   getting_started
   commands
   changelog
   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

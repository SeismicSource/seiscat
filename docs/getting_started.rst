Getting Started
===============

This page shows the typical first workflow with SeisCat:
create a config file, initialize a local database, and keep it updated.


Quick start
-----------

1. Create and enter a dedicated working directory:

.. code-block::

   mkdir -p /path/to/your_project
   cd /path/to/your_project

Using a dedicated directory keeps your ``seiscat.conf``, database file,
and downloaded event data in one place.

2. Show command help:

.. code-block::

   seiscat -h

3. Generate a sample configuration file:

.. code-block::

   seiscat sampleconfig

4. Edit the configuration file and initialize the database:

.. code-block::

   seiscat initdb

You can also initialize the database from local event files
(CSV, QuakeML, SC3ML, NLLOC, etc.):

.. code-block::

   seiscat initdb -f /path/to/your/catalog.csv
   seiscat initdb -f /path/to/your/events.xml


Typical SeisCat working directory
---------------------------------

A typical project directory after initialization looks like this:

.. code-block:: text

   your_project/
   ├── seiscat.conf
   ├── seiscat_db.sqlite           # created by seiscat initdb
   └── events/                     # created/used by seiscat fetchdata
       └── <event_id>/
           ├── waveforms/
           └── stations/

Where:

- ``seiscat.conf`` is your configuration file (created with
  ``seiscat sampleconfig``).
- ``seiscat_db.sqlite`` is your local SQLite catalog database,
  created by ``seiscat initdb``.
- ``events/`` contains per-event subdirectories when using
  ``seiscat fetchdata``.

All these names are configurable:

- Config file path/name: use ``-c/--configfile``
  (default: ``seiscat.conf``).
- Database file name: set ``db_file`` in the config file.
- Event directory name: set ``event_dir`` in the config file.
- Waveform and station subdirectories: set ``waveform_dir`` and
  ``station_dir`` in the config file.


Update an existing database
---------------------------

To update an existing database from an FDSN event webservice, run:

.. code-block::

   seiscat updatedb

If ``end_time`` is ``None``, SeisCat uses ``recheck_period`` to recheck the
last *n* days/hours/minutes/seconds.


Tab completion
--------------

SeisCat supports shell tab completion through
`argcomplete <https://kislyuk.github.io/argcomplete/>`__.

Enable it globally (one-time setup):

.. code-block::

   activate-global-python-argcomplete

Or add this line to your ``.bashrc`` or ``.zshrc``:

.. code-block::

   eval "$(register-python-argcomplete seiscat)"


Next
----

See the full command reference in :doc:`commands`.
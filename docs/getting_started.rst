Getting Started
===============

This page shows the typical first workflow with SeisCat:
create a config file, initialize a local database, and keep it updated.

If SeisCat is not installed yet, start with :doc:`installation`.


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

This creates a ``seiscat.conf`` file with default settings.
For a complete description of all available configuration options,
see :doc:`configuration_file`.

4. Edit the configuration file and initialize the database:

.. code-block::

   seiscat initdb

You can also initialize the database from local event files
(CSV, QuakeML, SC3ML, NLLOC, etc.):

.. code-block::

   seiscat initdb -f /path/to/your/catalog.csv
   seiscat initdb -f /path/to/your/events.xml
   seiscat initdb -f /path/to/your/catalog.csv -C

Use ``-C/--crop`` to apply the geographic/depth/magnitude/event-type
selection criteria from your configuration file when importing from local
files.


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
  ``seiscat sampleconfig``). See :doc:`configuration_file` for
  all available options.
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

You can also crop an existing local database to the configured selection
criteria (a backup is created first):

.. code-block::

   seiscat cropdb

If ``end_time`` is ``None``, SeisCat uses ``recheck_period`` to recheck the
last *n* days/hours/minutes/seconds.


Tab completion
--------------

Enable shell tab completion with:

.. code-block::

   seiscat self completion install


Running seiscat on a schedule (daemon mode)
-------------------------------------------

SeisCat can be run automatically on a fixed schedule using the operating
system's native scheduler: **launchd** on macOS and **systemd** on Linux.
Each scheduled invocation runs exactly one cycle (``updatedb``, plus
optional fetch stages) and then exits.

1. **Enable daemon mode** in your ``seiscat.conf``:

.. code-block::

   daemon_enabled          = True
   daemon_interval         = 15 minutes
   daemon_run_fetch_event  = False   # set True to also fetch QuakeML files
   daemon_run_fetch_data   = False   # set True to also fetch waveforms

Other optional keys: ``daemon_jitter_seconds``,
``daemon_lock_timeout_seconds``, ``daemon_log_file``,
``daemon_state_file``.
See :doc:`configuration_file` for full descriptions.

2. **Install the OS service** (user-scoped, no root required):

.. code-block::

   seiscat daemon install-service

The command generates the appropriate service artifact (launchd plist on
macOS, systemd unit + timer on Linux), installs it in the user-scope
service directory, and starts it immediately.
It also prints the commands to check service status and run a cycle
manually.

For a system-wide installation (requires root/sudo):

.. code-block::

   sudo seiscat daemon install-service --system

3. **Check status**:

.. code-block::

   seiscat daemon status

This reports the last cycle timestamp, per-stage timings, lock file
presence, and the OS service status.

4. **Run a cycle manually** (useful for testing):

.. code-block::

   seiscat daemon run

5. **Uninstall the service**:

.. code-block::

   seiscat daemon uninstall-service

**Recommendations**

- Keep your working directory (with ``seiscat.conf`` and the database) on a
  persistent, local filesystem so the scheduler can always find it.
- Use ``daemon_log_file`` to capture cycle output to a file (in addition to
  stdout, which is captured by launchd/systemd by default).
- Set a non-zero ``daemon_jitter_seconds`` if you run multiple seiscat
  instances starting at the same time to avoid simultaneous FDSN requests.

**Windows**

Native Windows service support (Task Scheduler) is not yet implemented.
On Windows, you can run ``seiscat daemon run`` manually or via a scheduled
task configured through the Task Scheduler GUI.


Next
----

See the full command reference in :doc:`commands` and
configuration options in :doc:`configuration_file`.
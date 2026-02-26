Commands
========

Below is a concise reference of all available commands and key options.

Common options
~~~~~~~~~~~~~~

- ``-c, --configfile PATH``: configuration file (default: ``seiscat.conf``).
- Event file input (``initdb``, ``updatedb``):

   - ``-f, --fromfile FILENAME``: read events from a file.
     Tries CSV format first, then falls back to ObsPy format
     auto-detection (QuakeML, SC3ML, NLLOC, etc.).
   - ``-d, --delimiter DELIM``: CSV delimiter (use ``\t`` for tab,
     ``" "`` for space). Default: auto. Only used for CSV files.
   - ``-n, --column_names NAME [NAME ...]``: column names (default:
     autodetect). Only used for CSV files.
   - ``-z, --depth_units {m,km}``: depth units (default: autodetect).
     Only used for CSV files.
- Selection and ordering (where supported: see per-command):

   - ``-w, --where "KEY OP VALUE [AND|OR KEY OP VALUE ...]"``:
     filter events.
   - ``-a, --allversions``: consider all versions of each event.
   - ``-r, --reverse``: reverse output order.

Filtering with ``--where``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use comparisons like ``=, <, >, <=, >=, !=`` and combine clauses with
``AND``/``OR`` (case-insensitive). Quote the whole expression to avoid
shell interpretation.

Examples:

.. code-block::

   seiscat print -w "depth < 10.0 AND mag >= 3.0"
   seiscat print -w "depth < 10.0 OR depth > 100.0"
   seiscat print -w "evid = aa1234bb"

seiscat initdb
~~~~~~~~~~~~~~

Initialize the database (from configured sources or an event file).

.. code-block::

   seiscat initdb                           # from config (e.g., FDSN)
   seiscat initdb -f catalog.csv            # from CSV
   seiscat initdb -f catalog.csv -z km      # explicit depth units
   seiscat initdb -f catalog.xml            # QuakeML (ObsPy auto-detect)
   seiscat initdb -f events.quakeml         # QuakeML (ObsPy auto-detect)
   seiscat initdb -f events.sc3ml           # SC3ML format

Options: ``--configfile``, event file input options, ``--depth_units``.

seiscat updatedb
~~~~~~~~~~~~~~~~

Update an existing database (honors ``recheck_period`` in the config).
Can also read new events from an event file.

.. code-block::

   seiscat updatedb
   seiscat updatedb -f catalog.csv
   seiscat updatedb -f events.xml

Options: ``--configfile``, event file input options, ``--depth_units``.

seiscat editdb
~~~~~~~~~~~~~~

Edit, replicate, or delete events in place.

.. code-block::

   # Edit a specific event (version autodetected unless specified)
   seiscat editdb EVID [EVENT_VERSION] -s key=value [-s key=value ...]

   # Increment numeric fields
   seiscat editdb EVID -i depth=3.0 -i mag=-0.5

   # Replicate or delete
   seiscat editdb EVID --replicate
   seiscat editdb EVID --delete --force

Options: ``--configfile``, ``--where`` (to target multiple events),
``--set KEY=VALUE`` (repeatable), ``--increment KEY=INCREMENT``
(repeatable), ``--replicate``, ``--delete``, ``--force``.

seiscat fetchdata
~~~~~~~~~~~~~~~~~

Fetch full event details (QuakeML), waveform data, or both. Optional
local SDS archive for waveforms.

.. code-block::

   # Download event details (QuakeML)
   seiscat fetchdata --event [EVID]

   # Download waveform data + StationXML
   seiscat fetchdata --data [--sds /path/to/SDS] [EVID]

   # Download both
   seiscat fetchdata --both [--sds /path/to/SDS] [EVID]

Options: ``--configfile``, ``--where``, ``--allversions``,
``--sds SDS_DIR``, one of ``--event`` | ``--data`` | ``--both``
(required), ``--overwrite_existing`` (only for event details).

seiscat print
~~~~~~~~~~~~~

Print the catalog to the console in various formats.

.. code-block::

   seiscat print                        # default table format
   seiscat print -f stats               # Summary statistics
   seiscat print EVID                   # Print a specific event
   seiscat print -w "mag >= 3.0"        # Filter and print

Options: ``--configfile``, ``--where``, ``--allversions``, ``--reverse``,
``--format {table,stats}``.

See also :ref:`seiscat export` for exporting to files.

seiscat export
~~~~~~~~~~~~~~

Export the catalog to a file in CSV, GeoJSON, or KML format.

.. code-block::

   seiscat export catalog.csv           # Export to CSV (format inferred)
   seiscat export catalog.json          # Export to GeoJSON
   seiscat export catalog.kml           # Export to KML
   seiscat export -f csv out.txt        # Explicit format (CSV)
   seiscat export -f json data.json     # Explicit format (GeoJSON)
   seiscat export -f kml map.kml        # Explicit format (KML)
   seiscat export catalog.csv -w "mag >= 3.0"  # Export filtered events
   seiscat export catalog.kml -s 8.0    # KML with custom marker size

Options: ``--configfile``, ``--where``, ``--allversions``, ``--reverse``,
``--format {csv,json,kml}`` (optional; if omitted, format is inferred from
the output file extension),
``--scale FLOAT`` (KML only; scale factor for marker size, default: 5.0).

seiscat plot
~~~~~~~~~~~~

Plot a catalog map using Cartopy, Folium, or Plotly.

.. code-block::

   seiscat plot -m cartopy              # Static map (default)
   seiscat plot -m folium               # Interactive leaflet map
   seiscat plot -m plotly -t            # Interactive Plotly with time slider
   seiscat plot --scale 8               # Marker size scale

Options: ``--configfile``, ``--where``, ``--allversions``, ``--reverse``,
``--maptype {cartopy,folium,plotly}``, ``--scale FLOAT``,
``--time_slider`` (Plotly only).

seiscat get
~~~~~~~~~~~

Get the value of a specific event attribute.

.. code-block::

   seiscat get key EVID [EVENT_VERSION]

Options: ``--configfile``.

seiscat set
~~~~~~~~~~~

Set the value of a specific event attribute.

.. code-block::

   seiscat set key value EVID [EVENT_VERSION]

Options: ``--configfile``.

seiscat run
~~~~~~~~~~~

Run a user-defined command for each selected event. All event columns are
exposed as environment variables (e.g., ``$evid``, ``$time``).
Supports concurrent execution safely against the database.

.. code-block::

   seiscat run "/path/to/script.sh"              # All selected events
   seiscat run "python myproc.py" AA123456        # Only this event
   seiscat run "./proc.sh" -w "mag >= 3.0" -r -a

Options: ``--configfile``, ``--where``, ``--allversions``, ``--reverse``.

seiscat sampleconfig
~~~~~~~~~~~~~~~~~~~~

Write a sample configuration file to the current directory.

.. code-block::

   seiscat sampleconfig

seiscat samplescript
~~~~~~~~~~~~~~~~~~~~

Write a sample script usable with ``seiscat run``.

.. code-block::

   seiscat samplescript

seiscat logo
~~~~~~~~~~~~

Print the SeisCat logo.

.. code-block::

   seiscat logo

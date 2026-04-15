Commands
========

Below is a concise reference of all available commands and key options.

For a complete description of all configuration file options,
see :doc:`configuration_file`.

Common options
~~~~~~~~~~~~~~

- ``-c, --configfile PATH``: configuration file (default: ``seiscat.conf``).
- Event file input (``initdb``, ``updatedb``):

   - ``-f, --fromfile FILE [FILE ...]``: read events from one or more files.
     Accepts multiple filenames. Tries CSV format first, then falls back to
     ObsPy format auto-detection (QuakeML, SC3ML, NLLOC, etc.).
   - **CSV field and delimiter auto-detection**: When reading CSV files,
     the tool automatically attempts to detect column meanings based on
     common name patterns (e.g., recognizes ``longitude``, ``lon``, as
     longitude, or ``evid``, ``event_id``, etc., as event ID).
     It also tries to infer the correct delimiter (comma, semicolon, tab,
     space) by analyzing the file. This "best effort" approach handles most
     CSV formats without additional configuration.
   - ``-d, --delimiter DELIM``: Override CSV delimiter auto-detection.
     Use ``\t`` for tab, ``" "`` for space, or any other character.
     Only used for CSV files.
   - ``-n, --column_names NAME [NAME ...]``: Override auto-detected column
     names by explicitly specifying the sequence of column meanings
     (e.g., ``-n time lat lon depth mag``). Only used for CSV files.
   - ``-x, --missing-value VALUE [VALUE ...]``: Treat one or more
     values/strings as missing values in CSV input.
     Single-value example: ``--missing-value -999``.
     Multiple-value example: ``--missing-value -999 N/A``.
     Only used for CSV files.
   - ``-z, --depth_units {m,km}``: Specify depth units if auto-detection
     fails or to override the detected value. Only used for CSV files.
   - ``-C, --crop``: when reading from file, crop events to the geographic,
     depth, magnitude, and event-type selection criteria from the config.
     Has no effect when importing from FDSN (criteria are already applied
     at query time).
- Selection and ordering (where supported: see per-command):

   - ``-w, --where "KEY OP VALUE [AND|OR KEY OP VALUE ...]"``:
     filter events.
   - ``--where-help``: display detailed help for the ``--where`` syntax
     with examples (formatted with syntax highlighting).
   - ``-a, --allversions``: consider all versions of each event.
   - ``--sortby FIELD``: sort output by any database field (default: ``time``).
     Common fields: ``time``, ``lat``, ``lon``, ``depth``, ``mag``, ``evid``.
     Supports tab-completion of available field names.
   - ``-r, --reverse``: reverse output order.

Filtering with ``--where``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use comparisons like ``=, <, >, <=, >=, !=`` and combine clauses with
``AND``/``OR`` (case-insensitive). Quote the whole expression to avoid
shell interpretation.

For missing values (SQL ``NULL``), use either SQL syntax or the shorthand
``None`` form:

- ``mag IS NULL`` (equivalent to ``mag=None`` or ``mag==None``)
- ``mag IS NOT NULL`` (equivalent to ``mag!=None``)

A bare field name is also accepted and uses SQL truthiness. For numeric
fields this means "non-null and non-zero":

- ``mag`` is equivalent to ``mag IS NOT NULL AND mag != 0``
- ``mag`` is not equivalent to ``mag!=None`` (because ``mag!=None`` keeps
  zero magnitudes)

For detailed help with the ``--where`` syntax, use ``--where-help``, e.g.:

.. code-block::

   seiscat print --where-help

This displays a formatted guide with field names, operators, and examples.

Examples:

.. code-block::

   seiscat print -w "depth < 10.0 AND mag >= 3.0"
   seiscat print -w "depth < 10.0 OR depth > 100.0"
   seiscat print -w "evid = aa1234bb"
   seiscat print -w "mag IS NULL"
   seiscat print -w "mag==None"
   seiscat print -w "mag!=None"
   seiscat export catalog.csv -w "time >= '2023-01-01' AND time < '2024-01-01'"
   seiscat plot -w "mag >= 4.0"

Sorting with ``--sortby``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Control the order of catalog output by sorting on any database field.
By default, events are sorted by ``time`` (oldest first). Use ``--reverse``
to reverse the sort order.

Common sort fields:

- ``time``: origin time (default)
- ``mag``: magnitude
- ``depth``: depth
- ``lat``, ``lon``: latitude, longitude
- ``evid``: event ID (alphabetical)

You can sort by any field in your database, including custom extra fields
defined in your configuration.

Examples:

.. code-block::

   seiscat print --sortby mag             # Sort by magnitude (smallest first)
   seiscat print --sortby mag --reverse   # Largest magnitude first
   seiscat print --sortby depth           # Sort by depth (shallowest first)
   seiscat export catalog.csv --sortby lat  # Sort by latitude
   seiscat plot --sortby time --reverse   # Plot with latest events on top

**Note**: When plotting with ``seiscat plot``, the sort order determines which
events are drawn on top. Using ``--sortby time`` (default) ensures the most
recent events appear on top of older ones. You can change this behavior to
emphasize other characteristics (e.g., ``--sortby mag`` to draw larger
magnitude events on top).

seiscat initdb
~~~~~~~~~~~~~~

Initialize the database (from configured sources or an event file).

.. code-block::

   seiscat initdb                           # from config (e.g., FDSN)
   seiscat initdb -f catalog.csv            # from CSV
   seiscat initdb -f catalog.csv -x -999    # one missing-value marker
   seiscat initdb -f catalog.csv -x -999 N/A  # two missing-value markers
   seiscat initdb -f catalog.csv -z km      # explicit depth units
   seiscat initdb -f catalog.xml            # QuakeML (ObsPy auto-detect)
   seiscat initdb -f events.quakeml         # QuakeML (ObsPy auto-detect)
   seiscat initdb -f events.sc3ml           # SC3ML format
   seiscat initdb -f catalog.csv -C         # crop to config criteria
   seiscat initdb -f catalog.csv --csv-extra-columns  # import extra CSV cols

Options: ``--configfile``, event file input options, ``--missing-value``,
``--depth_units``, ``--crop``, ``--csv-extra-columns``.

``--csv-extra-columns`` imports non-standard CSV columns as additional
database columns (TEXT) and fills them row-by-row. This option is supported
for ``seiscat initdb`` only.

seiscat updatedb
~~~~~~~~~~~~~~~~

Update an existing database (honors ``recheck_period`` in the config).
Can also read new events from an event file.

.. code-block::

   seiscat updatedb
   seiscat updatedb -f catalog.csv
   seiscat updatedb -f events.xml
   seiscat updatedb -f catalog.csv -C

Options: ``--configfile``, event file input options, ``--missing-value``,
``--depth_units``, ``--crop``.

seiscat cropdb
~~~~~~~~~~~~~~

Crop an existing database to the selection criteria defined in the
configuration file. A backup file (``<db_file>.bak``) is created first.

.. code-block::

   seiscat cropdb
   seiscat cropdb -c custom.conf

Options: ``--configfile``.

seiscat editdb
~~~~~~~~~~~~~~

Edit, replicate, or delete events in place.
It can also modify table columns (add/delete/rename).

.. code-block::

   # Edit a specific event (version autodetected unless specified)
   seiscat editdb EVID [EVENT_VERSION] -s key=value [-s key=value ...]

   # Increment numeric fields
   seiscat editdb EVID -i depth=3.0 -i mag=-0.5

   # Replicate or delete
   seiscat editdb EVID --replicate
   seiscat editdb EVID --delete --force

   # Edit table columns (global operations)
   seiscat editdb --add-column quality:TEXT
   seiscat editdb --rename-column quality=quality_flag
   seiscat editdb --delete-column quality_flag

Options: ``--configfile``, ``--where`` (to target multiple events),
``--set KEY=VALUE`` (repeatable), ``--increment KEY=INCREMENT``
(repeatable), ``--replicate``, ``--delete``, ``--add-column NAME[:TYPE]``,
``--rename-column OLD=NEW``, ``--delete-column NAME``, ``--force``.

Default columns (``evid``, ``ver``, ``time``, ``lat``, ``lon``, ``depth``,
``mag``, ``mag_type``, ``event_type``) are protected from rename/delete.
User-defined columns (from ``extra_field_*`` config options or added later)
are not protected and can be renamed/deleted.

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
   seiscat print --sortby mag -r        # Sort by magnitude (largest first)

Options: ``--configfile``, ``--where``, ``--allversions``, ``--sortby``,
``--reverse``, ``--format {table,stats}``.

**Interactive Pager**

When outputting a table to a terminal, ``seiscat print`` displays the catalog
using an interactive pager with the following features:

- **Vertical navigation**: Use ``j``/``↓`` to move down, ``k``/``↑`` to move up
- **Page navigation**: ``Space``/``f`` for next page, ``b`` for previous page,
  ``g`` for home, ``G`` for end
- **Horizontal scrolling**: If the table is wider than your terminal, use
  ``h``/``←`` and ``l``/``→`` to scroll left and right
- **Row selection**: The first row is highlighted; use ``j``/``k`` or arrow
  keys to move the selection
- **Event details popup**: Press ``Enter`` on the selected row to open a
  popup with all event fields listed line by line

   - In the popup, use ``j`` for next event and ``k`` for previous event
   - While moving with ``j``/``k``, the selected table row behind the popup is
     updated and auto-scrolled when needed
   - Use ``J``/``K`` or ``↓``/``↑`` to scroll inside the popup when details
     exceed the visible area
   - Press ``q``, ``Esc``, or ``Enter`` to close the popup
- **Copy event ID**: Press ``c`` to copy the event ID (evid) of the currently
  selected row to the system clipboard. A popup will confirm the copy
  operation.
- **Status bar**: Shows the number of visible events and total event count
- **Interactive sorting**:

  - Press ``s`` to open a popup menu to select a column to sort by
  - Press ``1``–``9`` to quickly sort by the corresponding column number
  - Press ``0`` to revert to the default sort order (from ``--sortby`` or
    configuration)
  - Press the same column again to toggle sort direction (ascending/descending)
  - The status bar shows the current sort field and direction (↑ for ascending,
    ↓ for descending)

- **Quit**: Press ``q`` or ``Esc`` to exit

To disable the pager and output plain text (useful for piping to a file or
other commands), redirect the output:

.. code-block::

   seiscat print > catalog.txt          # Save to file (no pager)
   seiscat print | head -10             # Pipe to another command (no pager)

See also :ref:`seiscat export` for exporting to files in specific formats.

.. _seiscat export:

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
   seiscat export catalog.csv --sortby depth  # Export sorted by depth

Options: ``--configfile``, ``--where``, ``--allversions``, ``--sortby``,
``--reverse``, ``--format {csv,json,kml}`` (optional; if omitted, format is
inferred from the output file extension),
``--scale FLOAT`` (KML only; scale factor for marker size, default: 5.0).

seiscat plot
~~~~~~~~~~~~

Plot a catalog map using Cartopy, Folium, or Plotly.

Cartopy and Plotly backends require optional dependencies installed with
``pip install seiscat[cartopy]`` or ``pip install seiscat[plotly]``.

.. code-block::

   seiscat plot -b cartopy              # Static map (default)
   seiscat plot -b folium               # Interactive leaflet map
   seiscat plot -b plotly -t            # Interactive Plotly with time slider
   seiscat plot --scale 8               # Marker size scale
   seiscat plot --colorby depth         # Color markers by a numeric field
   seiscat plot --colorby depth --colormap inferno
   seiscat plot --colorby depth --threshold 10
   seiscat plot --colorby time --threshold 2026-04-08T12:00:00Z
   seiscat plot --sortby mag -r         # Largest magnitudes drawn on top

Options: ``--configfile``, ``--where``, ``--allversions``, ``--sortby``,
``--reverse``, ``-b/--backend {cartopy,folium,plotly}``, ``--scale FLOAT``,
``--time_slider`` (Plotly only), ``--colorby FIELD``,
``--colormap NAME`` (Matplotlib colormap name; defaults to ``viridis``),
``--threshold VALUE`` (Cartopy + ``--colorby`` only).

``--threshold`` sets the value above which markers have a black outline.
Default is ``None``, meaning all markers have an outline.
When used with ``--colorby time``, ``VALUE`` can be either epoch seconds
or an ISO datetime string (for example, ``2026-04-08T12:00:00Z``).
When defined, the threshold is shown as a horizontal black line on the
colorbar.

A list of Matplotlib colormaps is available at this link:
`Matplotlib colormaps`_.

seiscat timeline
~~~~~~~~~~~~~~~~

Plot a timeline of the catalog either as attribute-vs-time scatter or
event-count-vs-time histogram.

Backends:

- ``matplotlib``: static figure on screen or file
- ``plotly``: interactive web figure on screen or HTML file
- ``terminal``: text chart of event counts over time

.. code-block::

   # Attribute vs time (default: magnitude)
   seiscat timeline
   seiscat timeline -A depth

   # Color markers by a second numeric attribute
   seiscat timeline -A depth --colorby mag
   seiscat timeline -A depth --colorby mag --colormap plasma

   # Use time as Y axis and/or colorbar attribute
   seiscat timeline -A time
   seiscat timeline -A mag --colorby time

   # Event count histogram with auto/custom bins
   seiscat timeline -C
   seiscat timeline -C -B 20
   seiscat timeline -C -B 7d
   seiscat timeline -C -B 1m

   # Cumulative count over raw event times (no bins)
   seiscat timeline --cumulative
   seiscat timeline -C --cumulative

   # Dual-axis: histogram with cumulative overlay
   seiscat timeline -C -B 20 --cumulative
   seiscat timeline -C -b plotly -B 1w --cumulative

   # Backend and output examples
   seiscat timeline -A mag -b matplotlib -o timeline.png
   seiscat timeline -A mag -b plotly -o timeline.html
   seiscat timeline -C -b terminal

Options: ``--configfile``, ``--where``, ``--allversions``,
``--attribute FIELD`` (default: ``mag``), ``--count``,
``--colorby FIELD`` (attribute mode only),
``--colormap NAME`` (attribute mode only; Matplotlib colormap name),
``-B/--bins SPEC`` (count mode only),
``-U/--cumulative`` (standalone cumulative mode or with ``--count``),
``--backend {matplotlib,plotly,terminal}``,
``--out-file FILE``.

A list of Matplotlib colormaps is available at this link:
`Matplotlib colormaps`_.

Bin specification for ``-B/--bins``:

- integer ``N``: use ``N`` equal-width bins
- duration string: ``Nd`` (days), ``Nw`` (weeks), ``Nm`` (months),
  ``Ny`` (years)
- omitted: automatic bin width
- ignored when ``--cumulative`` is used without ``--count``

Cumulative count behavior:

- With ``--cumulative`` only: plots raw cumulative count over chronological time (no binning)
- With ``--count`` only: plots histogram of binned event counts
- With both ``--count`` and ``--cumulative``: shows histogram on left y-axis and cumulative
   line from raw chronological events on right y-axis

Time formatting behavior:

- If ``--attribute time`` is used, Y-axis labels are formatted as time.
- If ``--colorby time`` is used, colorbar labels are formatted as time.
- This applies to both matplotlib and plotly backends.

seiscat get
~~~~~~~~~~~

Get the value of a specific event attribute.
If ``EVID`` is omitted, values are shown for all selected events.

.. code-block::

   seiscat get key [EVID] [EVENT_VERSION]

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
   seiscat run "./process.sh" --sortby mag        # Process by magnitude order

Options: ``--configfile``, ``--where``, ``--allversions``, ``--sortby``,
``--reverse``.

seiscat sampleconfig
~~~~~~~~~~~~~~~~~~~~

Write a sample configuration file to the current directory.

.. code-block::

   seiscat sampleconfig

For a complete description of all configuration options,
see :doc:`configuration_file`.

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


.. Links ---
.. _Matplotlib colormaps: https://matplotlib.org/stable/users/explain/colors/colormaps.html
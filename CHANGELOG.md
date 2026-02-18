# SeisCat Changelog

Keep a local seismic catalog.

Copyright (c) 2022-2026 Claudio Satriano <satriano@ipgp.fr>

## unreleased

- Raised minimum required Python version to 3.9, added support for Python
  3.13 and 3.14
- `seiscat download` renamed to `seiscat fetchdata`
- New option for `seiscat fetchdata`: `--sds` to retrieve waveform data from
  a local SDS archive
- Configuration option `channel_priorities` replaced by `channel_codes`
- Removed configuration option `location_priorities`
- Added configuration option `prefer_high_sampling_rate`
- New option for `seiscat initdb` and `seiscat updatedb`: `--fromfile` to
  initialize or update the database from a CSV file
- New command `seiscat run` to run a user-defined command on each event
- New command `seiscat samplescript` to write a sample script for the
  `seiscat run` command
- New command `seiscat export` to export the catalog to a file in
  a specified format (currently supported formats are CSV and GeoJSON)
- `seiscat print`: remove the CSV format, which is now available
  through `seiscat export`
- New commands `seiscat get` and `seiscat set` to get and set the value of
  a specfic event attribute
- New plottype `plotly` for `seiscat plot`, producing interactive 3D seismicity
  plots
- New command `seiscat logo` to print the beautiful, ascii-art SeisCat logo
- New option for `seiscat plot`: `--out-file` to save the plot to a file
- Use higher resolution Natural Earth background images for Cartopy maps
- Fixed an issue in `seiscat editdb` where positional arguments (`eventid` and
  `event_version`) were not parsed correctly due to improper handling of the
  `--set` and `--increment` options. Users must now repeat the `--set` and
  `--increment` options for each `KEY=VALUE` pair
  (e.g., `-s locked=True -s processed=True`).

## v0.8 - 2024-10-28

- New option for `seiscat print` and `seiscat plot`: `--where` to filter events
  based on one or more conditions
- New option for `seiscat plot`: `--maptype` to use either `cartopy`
  (Matplotlib) or `folium` (HTML) for plotting maps
- New command line option `seiscat download` to download full event details
  and/or waveform data and metadata from FDSNWS services

## v0.7 - 2024-03-11

- CSV output for `seiscat print`, using `--format=csv` (or `-f csv`)
- Special argument `ALL` for `seiscat editdb` to edit all the events
  (or all the events of a given version when used together with the
  `--version` argument)
- New option for `seiscat editdb`: `--increment` to increment (or decrement)
  a numeric field by a given, positive or negative, amount

## v0.6 - 2023-06-26

- New command to edit the event database: `seiscat editdb`
- `eventid` argument for `seiscat print`, to print a specific event
- Fix bug where an event was updated when extra fields were set to a different
  value than the default
- Fix bug where an event was updated to new version even if the same event
  already existed in the database

## v0.5 - 2023-06-22

- New configuration option: `overwrite_updated_events`. Default is `False`
  and updated events get an incremented version number
- `--allversions` option for `seiscat print` and `seiscat plot` to print/show
  all the versions for events with more than one version
- `--format` option for `seiscat print`: current possibilities are `table`
  (default) and `stats`
- `--reverse` option for `seiscat print`: if set, latest events will be printed
  on top
- Rename database column `dep` to `depth`

## v0.4 - 2023-06-20

- Command line autocompletion, thanks to argcomplete
- Show event depth in plot annotation
- `--scale` option for `seiscat plot`
- Correctly parse evids from USGS and ISC
- Exit gracefully if database file is missing
- Fix printing of `None` values

## v0.3 - 2023-06-20

- New command to print catalog to screen: `seiscat print`
- Documentation!

## v0.2 - 2023-06-19

- Fix for plotting the whole world when no limits are given
- New way of computing zoom level for map tiles

## v0.1 - 2023-06-19

This is the initial release of SeisCat.

SeisCat is a command line tool to keep a local seismic catalog.
The local catalog can be used as a basis for further analyses.

The seismic catalog is built and updated by querying a FDSNWS event webservice.
More ways of feeding the catalog will be added in the future.

The local catalog is stored in a SQLite database (single file database).

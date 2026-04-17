# SeisCat Changelog

Keep a local seismic catalog.

Copyright (c) 2022-2026 Claudio Satriano <satriano@ipgp.fr>

## [unreleased]

### Added

- New config options `fdsn_event_user` and `fdsn_event_password` to specify
  authentication credentials for the FDSN event web service (`fdsn_event_url`).
- New config options `fdsn_providers_users` and `fdsn_providers_passwords`
  (parallel lists) to specify per-provider authentication credentials for
  waveform/metadata providers (`fdsn_providers`).
- New config option `keep_raw_evid` (default: `False`). When `True`, the full
  original `resource_id` string is stored in an additional protected column
  `raw_evid` alongside the normalized `evid`. This is useful when the
  normalized evid is not recognized by the FDSN server and the original
  resource_id is needed to download event details.
- `seiscat fetchdata`: when downloading event details fails with the
  normalized `evid`, automatically retry using the `raw_evid` value (if the
  `raw_evid` column is present in the database).
- New `--max-col-width` option for `seiscat print` to limit the width of
  columns in the interactive table pager. Longer values are truncated with
  `...`, while full row details remain available via the Enter popup.
- `seiscat print` interactive event sorting popup:
  - option to restore the default sort order by pressing ``0``
  - it's now possible to dismiss the event sorting popup
    by pressing ``esc`` or ``q``.

### Fixed

- Fixed pager sorting failing when a column contains `None` values mixed with
  numeric values (e.g. magnitude columns with positive and negative values).
- Fixed `seiscat plot -b cartopy` crashing with `IndexError` when the map
  extent is very small (e.g. near-coincident events), by falling back to the
  simple background when Natural Earth imagery cannot be rendered.
- Fixed clipboard copying of evid not working on linux.

## [0.9] - 2026-04-15

This is a major release with substantial improvements across visualization,
database management, and workflow automation. Highlights include a new
interactive terminal UI, expanded plotting capabilities with Plotly, and four
new core commands: `seiscat timeline`, `seiscat export`, `seiscat cropdb`, and
`seiscat run`. Additional enhancements throughout the CLI make filtering,
import/export, and event processing more powerful and flexible.

Minimum required Python version is now 3.9, and support for Python
3.13 and 3.14 has been added.

See the full changelog below for complete details.

### Added

#### Compatibility

- Added support for Python 3.13 and 3.14.

#### CLI and User Interface

- Added colored help output using `rich-argparse`.
- Added colorized error messages for improved visibility and consistency.
- Added interactive table pager for `seiscat print -f table` with:
  - fixed header
  - alternating row colors
  - row selection
  - sorting
  - copying evid
  - keyboard navigation
  - event details popup
- Added new `seiscat logo` command to print the ASCII-art SeisCat logo.

#### Filtering and Sorting

- Added new `--where-help` option to display detailed help for the `--where`
  filter expression, including syntax, examples, and notes. Available from any
  subcommand supporting `--where` (`editdb`, `print`, `export`, `plot`,
  `fetchdata`, `run`).
- Added new `--sortby` option to sort catalog output by any database field
  (default: `time`). Available for:
  - `seiscat print`
  - `seiscat export`
  - `seiscat plot`
  - `seiscat run`
- Added tab-completion support for `--sortby` field names.

#### Plotting and Visualization

- Added new `seiscat timeline` command with:
  - matplotlib / plotly / terminal backends
  - attribute or count mode (`--count`, `--bins`)
  - optional `--colorby`
  - time-formatted axis/colorbar when using `time`
- Added `--colorby` support for map plots.
- Added `--colormap` support (with autocompletion) for:
  - `seiscat plot`
  - `seiscat timeline`
- Added new `--threshold` option for `seiscat plot` (Cartopy + `--colorby`
  only): markers above threshold retain a black outline.
- Added new `plotly` plottype for `seiscat plot`, enabling interactive 3D
  seismicity plots.
- Added new `--out-file` option for `seiscat plot` to save plots to file.

#### Data Import and Export

- Added `--fromfile` option to `seiscat initdb` and `seiscat updatedb` to
  initialize/update the database from an event file.
  Supported formats:
  - CSV
  - Any ObsPy-supported format (QuakeML, SC3ML, NLLOC, etc.)
- Added `-C, --crop` option for file-based imports in `seiscat initdb` and
  `seiscat updatedb` to crop imported events according to configured selection
  criteria.
- Added new CSV import option `-x, --missing-value` in `seiscat initdb` and
  `seiscat updatedb` to define missing-value markers (e.g. `-999`, `N/A`).
- Added new `--csv-extra-columns` option to `seiscat initdb` for importing
  non-standard CSV columns as additional database fields.
- Added new `seiscat export` command to export catalogs in:
  - CSV
  - GeoJSON
  - KML

#### Database Management

- Added new `seiscat cropdb` command to crop an existing database to configured
  selection criteria.
- Added `seiscat editdb` options to:
  - add table columns
  - delete table columns
  - rename table columns
- Added protection for default columns against rename/delete.
- Added new `seiscat get` and `seiscat set` commands to retrieve/set specific
  event attribute values.

#### Automation and Scripting

- Added new `seiscat run` command to run a user-defined command on each event.
- Added new `seiscat samplescript` command to generate a sample script for
  `seiscat run`.

#### Data Retrieval

- Added new `--sds` option for `seiscat fetchdata` to retrieve waveform data
  from a local SDS archive.

#### Configuration

- Added new configuration option `prefer_high_sampling_rate`.
- Added new configuration option `station_radius_max_mag` for
  magnitude-dependent maximum station radius.

### Changed

- Raised minimum required Python version to 3.9.
- Changed default database filename from `seiscat.sqlite` to
  `seiscat_db.sqlite`.
- Improved error messages for `--where` to suggest using `--where-help`.
- Improved `--where` handling of missing values:
  - `mag=None`
  - `mag==None`
  - `mag!=None`
  are now translated into SQL `IS NULL` / `IS NOT NULL`.
- Renamed `-m/--maptype` to `-b/--backend` in `seiscat plot` for consistency
  with `seiscat timeline`.
- Renamed `seiscat download` to `seiscat fetchdata`.
- Replaced configuration option `channel_priorities` with `channel_codes`.
- `seiscat plot` now respects `--sortby` instead of always sorting by time,
  allowing control over draw order.
- Upgraded Cartopy maps to use higher-resolution Natural Earth background
  images.
- `seiscat editdb` now requires repeating `--set` and `--increment` for each
  `KEY=VALUE` pair. Example: `-s locked=True -s processed=True`.

### Removed

- Removed configuration option `location_priorities`.
- Removed CSV output format from `seiscat print`; use `seiscat export` instead.

### Fixed

- Fixed an issue in seiscat editdb where positional arguments (`eventid`,
`event_version`) were not parsed correctly due to improper handling of
`--set` and `--increment`.

## [0.8] - 2024-10-28

- New option for `seiscat print` and `seiscat plot`: `--where` to filter events
  based on one or more conditions
- New option for `seiscat plot`: `--maptype` to use either `cartopy`
  (Matplotlib) or `folium` (HTML) for plotting maps
- New command line option `seiscat download` to download full event details
  and/or waveform data and metadata from FDSNWS services

## [0.7] - 2024-03-11

- CSV output for `seiscat print`, using `--format=csv` (or `-f csv`)
- Special argument `ALL` for `seiscat editdb` to edit all the events
  (or all the events of a given version when used together with the
  `--version` argument)
- New option for `seiscat editdb`: `--increment` to increment (or decrement)
  a numeric field by a given, positive or negative, amount

## [0.6] - 2023-06-26

- New command to edit the event database: `seiscat editdb`
- `eventid` argument for `seiscat print`, to print a specific event
- Fix bug where an event was updated when extra fields were set to a different
  value than the default
- Fix bug where an event was updated to new version even if the same event
  already existed in the database

## [0.5] - 2023-06-22

- New configuration option: `overwrite_updated_events`. Default is `False`
  and updated events get an incremented version number
- `--allversions` option for `seiscat print` and `seiscat plot` to print/show
  all the versions for events with more than one version
- `--format` option for `seiscat print`: current possibilities are `table`
  (default) and `stats`
- `--reverse` option for `seiscat print`: if set, latest events will be printed
  on top
- Rename database column `dep` to `depth`

## [0.4] - 2023-06-20

- Command line autocompletion, thanks to argcomplete
- Show event depth in plot annotation
- `--scale` option for `seiscat plot`
- Correctly parse evids from USGS and ISC
- Exit gracefully if database file is missing
- Fix printing of `None` values

## [0.3] - 2023-06-20

- New command to print catalog to screen: `seiscat print`
- Documentation!

## [0.2] - 2023-06-19

- Fix for plotting the whole world when no limits are given
- New way of computing zoom level for map tiles

## [0.1] - 2023-06-19

This is the initial release of SeisCat.

SeisCat is a command line tool to keep a local seismic catalog.
The local catalog can be used as a basis for further analyses.

The seismic catalog is built and updated by querying a FDSNWS event webservice.
More ways of feeding the catalog will be added in the future.

The local catalog is stored in a SQLite database (single file database).

[unreleased]: https://github.com/SeismicSource/seiscat/compare/v0.9...HEAD
[0.9]: https://github.com/SeismicSource/seiscat/compare/v0.8...v0.9
[0.8]: https://github.com/SeismicSource/seiscat/compare/v0.7...v0.8
[0.7]: https://github.com/SeismicSource/seiscat/compare/v0.6...v0.7
[0.6]: https://github.com/SeismicSource/seiscat/compare/v0.5...v0.6
[0.5]: https://github.com/SeismicSource/seiscat/compare/v0.4...v0.5
[0.4]: https://github.com/SeismicSource/seiscat/compare/v0.3...v0.4
[0.3]: https://github.com/SeismicSource/seiscat/compare/v0.2...v0.3
[0.2]: https://github.com/SeismicSource/seiscat/compare/v0.1...v0.2
[0.1]: https://github.com/SeismicSource/seiscat/releases/tag/v0.1

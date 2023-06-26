# SeisCat Changelog

Keep a local seismic catalog.

Copyright (c) 2022-2023 Claudio Satriano <satriano@ipgp.fr>

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

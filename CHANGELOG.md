# SeisCat Changelog

Keep a local seismic catalog.

Copyright (c) 2022-2023 Claudio Satriano <satriano@ipgp.fr>

## Unreleased

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

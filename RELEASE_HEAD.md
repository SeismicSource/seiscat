# SeisCat

Keep a local seismic catalog.

Copyright (c) 2022-2026 Claudio Satriano <satriano@ipgp.fr>

---
SeisCat is an open-source command-line tool for keeping and querying a local seismic catalog.

Source code:
[github.com/SeismicSource/seiscat](https://github.com/SeismicSource/seiscat)

Documentation:
[seiscat.readthedocs.io](https://seiscat.readthedocs.io/en/stable/)

If you use SeisCat in your work, please cite:

> Satriano, C. (2026). SeisCat: Keep a local seismic catalog (X.Y). doi: 10.5281/ZENODO.8411836

Replace X.Y with the specific SeisCat version number used in your study.

       /\_/\
    ~~( ⊙.⊙ )~~ SeisCat

## Changes in this version:

### Added

- New `station_codes` configuration parameter for filtering stations by name
  when downloading waveforms (analogous to `channel_codes`).
  Supports multiple codes and wildcard patterns (`?`, `*`).
- New `picked_stations_only` configuration parameter to restrict waveform
  downloads to stations that have at least one P or S-wave arrival in the
  catalog (requires a QuakeML event details file to be present).

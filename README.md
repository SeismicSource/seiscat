# SeisCat

Keep a local seismic catalog.

[![PyPI-badge]][PyPI-link]
[![license-badge]][license-link]

(c) 2022-2023 Claudio Satriano <satriano@ipgp.fr>

## Overview

SeisCat is a command line tool to keep a local seismic catalog.
The local catalog can be used as a basis for further analyses.

The seismic catalog is built and updated by querying a FDSNWS event webservice.
More ways of feeding the catalog will be added in the future.

The local catalog is stored in a SQLite database (single file database).

## Getting Started

To get help:

    seiscat -h

## Installation

### Installing the latest release

#### Using pip and PyPI (preferred method)

The latest release of SeisCat is available on the
[Python Package Index](https://pypi.org/project/seiscat/).

You can install it easily through `pip`:

    pip install seiscat

To upgrade from a previously installed version:

    pip install --upgrade seiscat

#### From SeisCat GitHub releases

Download the latest release from the
[releases page](https://github.com/SeismicSource/seiscat/releases),
in `zip` or `tar.gz` format, then:

    pip install seiscat-X.Y.zip

or

    pip install seiscat-X.Y.tar.gz

Where, `X.Y` is the version number (e.g., `0.1`).
You don't need to uncompress the release files yourself.

### Installing a developer snapshot

If you need a recent feature that is not in the latest release (see the
`unreleased` section in [CHANGELOG](CHANGELOG.md)), you want to use the more
recent development snapshot from the
[SeisCat GitHub repository](https://github.com/SeismicSource/seiscat).

#### Using pip (preferred method)

The easiest way to install the most recent development snapshot is to download
and install it through `pip`, using its builtin `git` client:

    pip install git+https://github.com/SeismicSource/seiscat.git

Run this command again, from times to times, to keep SeisCat updated with
the development version.

### Cloning the SeisCat GitHub repository

If you want to take a look at the source code (and possibly modify it 😉),
clone the project using `git`:

    git clone https://github.com/SeismicSource/seiscat.git

or, using SSH:

    git clone git@github.com:SeismicSource/seiscat.git

(avoid using the "Download ZIP" option from the green "Code" button, since
version number is lost).

Then, go into the `seiscat` main directory and install the code in "editable
mode" by running:

    pip install -e .

You can keep your local SeisCat repository updated by running `git pull`
from times to times. Thanks to `pip`'s "editable mode", you don't need to
reinstall SeisCat after each update.

<!-- Badges and project links -->
[PyPI-badge]: http://img.shields.io/pypi/v/seiscat.svg
[PyPI-link]: https://pypi.python.org/pypi/seiscat
[license-badge]: https://img.shields.io/badge/license-GPLv3-green
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html

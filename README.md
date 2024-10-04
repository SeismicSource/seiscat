# SeisCat

Keep a local seismic catalog.

[![changelog-badge]][changelog-link]
[![PyPI-badge]][PyPI-link]
[![license-badge]][license-link]
[![docs-badge]][docs-link]

Copyright (c) 2022-2024 Claudio Satriano <satriano@ipgp.fr>

## Overview

SeisCat is a command line tool to keep a local seismic catalog.
The local catalog can be used as a basis for further analyses.

The seismic catalog is built and updated by querying a FDSNWS event webservice.
More ways of feeding the catalog will be added in the future.

The local catalog is stored in a SQLite database (single file database).

👇  See below on how to [install](#installation) and
[get started](#getting-started).

📖 Check out the official documentation [here](https://seiscat.rtfd.io).

## Getting Started

To get help:

    seiscat -h

First thing to do is to generate a sample configuration file:

    seiscat sampleconfig

Then, edit the configuration file and init the database:

    seiscat initdb

To keep the database updated, run on a regular basis:

    seiscat updatedb

(This will use the configuration parameter `recheck_period` to recheck the
last *n* days or hours).

You can edit the attributes of specific events in the database using:

    seiscat editdb

You can print the catalog to screen:

    seiscat print

Or plot it:

    seiscat plot

Each of the above commands can have its own options.
As an example, to discover the options for the `plot` command, try:

    seiscat plot -h

SeisCat supports command line tab completion for arguments, thanks to
[argcomplete](https://kislyuk.github.io/argcomplete/).
To enable command line tab completion run:

    activate-global-python-argcomplete

(This is a one-time command that needs to be run only once).

Or, alternatively, add the following line to your `.bashrc` or `.zshrc`:

    eval "$(register-python-argcomplete seiscat)"

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

## Getting Help / Reporting Bugs

### 🙏 I need help

Please open an [Issue][Issues].

### 🐞 I found a bug

Please open an [Issue][Issues].

## Contributing

I'm very open to contributions: if you have new ideas, please open an
[Issue][Issues].
Don't hesitate sending me pull requests with new features and/or bugfixes!

<!-- Badges and project links -->
[changelog-badge]: https://img.shields.io/badge/Changelog-136CB6.svg
[changelog-link]: CHANGELOG.md
[PyPI-badge]: http://img.shields.io/pypi/v/seiscat.svg
[PyPI-link]: https://pypi.python.org/pypi/seiscat
[license-badge]: https://img.shields.io/badge/license-GPLv3-green
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[docs-badge]: https://readthedocs.org/projects/seiscat/badge/?version=latest
[docs-link]: https://seiscat.readthedocs.io/en/latest/?badge=latest
[Issues]: https://github.com/SeismicSource/seiscat/issues

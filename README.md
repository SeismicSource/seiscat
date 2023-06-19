# SeisCat

Keep a local seismic catalog

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

### From SeisCat GitHub repository

If you need a recent feature that is not in the latest release (see the
`unreleased` section in [CHANGELOG](CHANGELOG.md)), you want to use the source
code from the
[SeisCat GitHub repository](https://github.com/SeismicSource/SeisCat).

For that, clone the project:

    git clone https://github.com/SeismicSource/seiscat.git

(avoid using the "Download ZIP" option from the green "Code" button, since
version number is lost), then install the code from within the `seiscat`
main directory by running:

    pip install .

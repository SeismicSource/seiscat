# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
A minimal setup script for Seiscat

This script ensures compatibility with versioneer
and dynamically generates a README for correctly resolving paths on GitHub.

All the remaining configuration is in pyproject.toml.
"""
from setuptools import setup
import versioneer

# Dynamically generate the README text for PyPI, replacing local paths
# with the corresponding URLs on GitHub and image paths with the corresponding
# URLs on the CDN.
GITHUB_BASEURL = 'https://github.com/SeismicSource/seiscat/blob/main'
revision = versioneer.get_versions()['full-revisionid']
cdn_baseurl = f'https://cdn.jsdelivr.net/gh/SeismicSource/seiscat@{revision}'
with open('README.md', 'rb') as f:
    long_description = f.read().decode('utf-8').replace(
        ': CHANGELOG.md',
        f': {GITHUB_BASEURL}/CHANGELOG.md'
    ).replace(
        'imgs/SeisCat_logo.svg',
        f'{cdn_baseurl}/imgs/SeisCat_logo.svg'
    )

setup(
    long_description=long_description,
    long_description_content_type='text/markdown',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass()
)

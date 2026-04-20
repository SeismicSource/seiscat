# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install-context detection for seiscat self commands."""
from __future__ import annotations

from dataclasses import dataclass
import json
from importlib import metadata
from .._version import get_versions


@dataclass
class InstallContext:
    """Detected install context for SeisCat."""
    installer: str
    channel: str
    version_installed: str
    source_url: str | None
    editable: bool
    confidence: str


def detect_install_context(dist_name='seiscat'):
    """Detect installer/channel metadata for the installed distribution."""
    try:
        dist = metadata.distribution(dist_name)
    except metadata.PackageNotFoundError:
        return InstallContext(
            installer='unknown',
            channel='unknown',
            version_installed='unknown',
            source_url=None,
            editable=False,
            confidence='low',
        )

    installer = (
        (dist.read_text('INSTALLER') or '').strip().lower() or 'unknown'
    )
    version_installed = get_versions().get('version', dist.version)
    source_url = None
    editable = False
    channel = 'release'
    confidence = 'medium'

    if direct_url_raw := dist.read_text('direct_url.json'):
        try:
            direct_url = json.loads(direct_url_raw)
            source_url = direct_url.get('url')
            editable = bool(
                direct_url.get('dir_info', {}).get('editable', False)
            )
            vcs_info = direct_url.get('vcs_info') or {}
            is_git_source = source_url and (
                source_url.startswith('git+') or source_url.endswith('.git')
            )
            if editable:
                channel = 'editable'
            elif vcs_info or is_git_source:
                channel = 'git'
            else:
                channel = 'release'
            confidence = 'high'
        except (TypeError, ValueError):
            confidence = 'low'

    if installer not in {'pip', 'uv'}:
        installer = 'unknown'

    return InstallContext(
        installer=installer,
        channel=channel,
        version_installed=version_installed,
        source_url=source_url,
        editable=editable,
        confidence=confidence,
    )

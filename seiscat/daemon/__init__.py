# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
seiscat.daemon — scheduled one-shot daemon mode.

Public API re-exported from the submodules:
  - cycle.py   : one-shot cycle orchestration and lock/state helpers
  - services.py: OS service artifact generation (launchd / systemd)

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from .cycle import (  # noqa: F401
    _acquire_lock,
    _default_state_dir,
    _load_state,
    _lock_file_path,
    _persist_and_release,
    _pid_alive,
    _read_lock,
    _release_lock,
    _resolve_state_file,
    _run_fetch_data,
    _run_fetch_event,
    _run_updatedb,
    _save_state,
    _setup_logging,
    _write_lock,
    parse_interval_seconds,
    run_daemon_cycle,
)
from .services import (  # noqa: F401
    _LAUNCHD_LABEL,
    _SYSTEMD_SERVICE,
    _SYSTEMD_TIMER,
    install_service,
    render_launchd_plist,
    render_systemd_service,
    render_systemd_timer,
    run_daemon_command,
    show_status,
    uninstall_service,
)

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Daemon mode: one-shot cycle orchestration for seiscat.

Designed to be invoked by launchd (macOS) or systemd (Linux) on a schedule.
Each invocation runs exactly one cycle:
  1. updatedb (always)
  2. fetch event details (if daemon_run_fetch_event is True)
  3. fetch waveform data (if daemon_run_fetch_data is True)

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import hashlib
import json
import logging
import os
import pathlib
import random
import sys
import time

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: default state/lock directory
# ---------------------------------------------------------------------------

def _default_state_dir():
    """Return the default directory for state and lock files."""
    if sys.platform == 'darwin':
        return (
            pathlib.Path.home() / 'Library' / 'Application Support' / 'seiscat'
        )
    if xdg := os.environ.get('XDG_STATE_HOME', ''):
        return pathlib.Path(xdg) / 'seiscat'
    return pathlib.Path.home() / '.local' / 'state' / 'seiscat'


def _instance_tag(config):
    """Return an 8-char hex tag unique to this instance's db_file path."""
    db_file = config.get('db_file', '')
    return hashlib.sha256(str(db_file).encode()).hexdigest()[:8]


def _resolve_state_file(config):
    """Return the resolved Path for the daemon state file."""
    raw = config.get('daemon_state_file', None)
    default_state_file = f'daemon_state.{_instance_tag(config)}.json'
    return (
        pathlib.Path(raw)
        if raw
        else _default_state_dir() / default_state_file
    )


def _lock_file_path(config):
    """Return the Path for the daemon lock file, unique per db_file."""
    return _default_state_dir() / f'daemon.{_instance_tag(config)}.lock'


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(config):
    """Configure logging to stdout and optional file."""
    log_file = config.get('daemon_log_file', None)
    fmt = '%(asctime)s [%(levelname)s] %(message)s'
    datefmt = '%Y-%m-%dT%H:%M:%SZ'
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_path = pathlib.Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding='utf-8'))
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )


# ---------------------------------------------------------------------------
# Lock management
# ---------------------------------------------------------------------------

def _read_lock(lock_path):
    """Read the lock file and return (pid, timestamp) or (None, None)."""
    try:
        data = json.loads(lock_path.read_text(encoding='utf-8'))
        return int(data['pid']), float(data['ts'])
    except Exception:  # noqa: BLE001
        return None, None


def _write_lock(lock_path):
    """Write a lock file with the current PID and timestamp."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps({'pid': os.getpid(), 'ts': time.time()}),
        encoding='utf-8',
    )


def _pid_alive(pid):
    """Return True if the process with *pid* is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _acquire_lock(config):
    """
    Acquire the daemon single-instance lock.

    Returns True on success, False if another live instance holds the lock.
    Stale locks (holding process dead, or age > daemon_lock_timeout_seconds)
    are removed before a new lock is written.
    """
    lock_path = _lock_file_path(config)
    timeout = config.get('daemon_lock_timeout_seconds', 300)
    if lock_path.exists():
        pid, ts = _read_lock(lock_path)
        if pid is not None:
            age = time.time() - (ts or 0)
            if _pid_alive(pid):
                if timeout > 0 and age > timeout:
                    logger.warning(
                        'Stale lock (pid=%d, age=%.0fs > timeout=%ds); '
                        'removing it.',
                        pid, age, timeout,
                    )
                    lock_path.unlink(missing_ok=True)
                else:
                    logger.warning(
                        'Another daemon instance is running (pid=%d). '
                        'Skipping this cycle.',
                        pid,
                    )
                    return False
            else:
                logger.info(
                    'Removing stale lock from dead process (pid=%d).', pid
                )
                lock_path.unlink(missing_ok=True)
        else:
            # Corrupt lock – remove it
            lock_path.unlink(missing_ok=True)
    _write_lock(lock_path)
    return True


def _release_lock(config):
    """Remove the daemon lock file if it belongs to the current process."""
    lock_path = _lock_file_path(config)
    pid, _ = _read_lock(lock_path)
    if pid == os.getpid():
        lock_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state(config):
    """Load existing state from the state file, or return an empty dict."""
    state_file = _resolve_state_file(config)
    if not state_file or not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding='utf-8'))
    except Exception:  # noqa: BLE001
        return {}


def _save_state(config, state):
    """Persist state dict to the state file."""
    state_file = _resolve_state_file(config)
    if state_file is None:
        return
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(state, indent=2), encoding='utf-8'
    )


# ---------------------------------------------------------------------------
# Interval parsing
# ---------------------------------------------------------------------------

_INTERVAL_UNITS = {
    'second': 1, 'seconds': 1,
    'minute': 60, 'minutes': 60,
    'hour': 3600, 'hours': 3600,
    'day': 86400, 'days': 86400,
}


def parse_interval_seconds(interval_str):
    """
    Parse a daemon_interval string such as "15 minutes" and return seconds.

    :param interval_str: duration string
    :returns: number of seconds (int)
    :raises ValueError: if the string cannot be parsed
    """
    parts = str(interval_str).strip().split()
    if len(parts) != 2:
        raise ValueError(
            f'Cannot parse daemon_interval {interval_str!r}. '
            'Expected format: "X unit" (e.g. "15 minutes").'
        )
    try:
        value = int(parts[0])
    except ValueError as err:
        raise ValueError(
            f'Cannot parse daemon_interval {interval_str!r}: '
            f'{parts[0]!r} is not an integer.'
        ) from err
    unit = parts[1].lower()
    if unit not in _INTERVAL_UNITS:
        raise ValueError(
            f'Unknown time unit {unit!r} in daemon_interval. '
            f'Allowed: {", ".join(sorted(set(_INTERVAL_UNITS)))}.'
        )
    return value * _INTERVAL_UNITS[unit]


# ---------------------------------------------------------------------------
# Cycle stages
# ---------------------------------------------------------------------------

def _run_updatedb(config):
    """Run one updatedb cycle and return elapsed seconds."""
    from ..database.feeddb import feeddb
    args = config['args']
    if not hasattr(args, 'fromfile'):
        args.fromfile = None
    if not hasattr(args, 'crop'):
        args.crop = False
    t0 = time.monotonic()
    feeddb(config, initdb=False)
    return time.monotonic() - t0


def _run_fetch_event(config):
    """Fetch event details for all events; return elapsed seconds."""
    from ..fetchdata.event_details import fetch_event_details
    t0 = time.monotonic()
    fetch_event_details(config)
    return time.monotonic() - t0


def _run_fetch_data(config):
    """Fetch waveform data for all events; return elapsed seconds."""
    from ..fetchdata.event_waveforms import fetch_event_waveforms
    t0 = time.monotonic()
    fetch_event_waveforms(config)
    return time.monotonic() - t0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_daemon_cycle(config):
    """
    Execute one daemon cycle.

    Steps:
      1. Apply startup jitter (if configured).
      2. Acquire single-instance lock (exit cleanly if another is running).
      3. Run updatedb.
      4. Optionally run fetch event details.
      5. Optionally run fetch waveform data.
      6. Persist stage durations and final status to the state file.
      7. Release the lock.

    :param config: seiscat config dict (must include 'args' key)
    """
    _setup_logging(config)
    logger.info('=== seiscat daemon cycle starting ===')

    # Startup jitter
    jitter = config.get('daemon_jitter_seconds', 0)
    if jitter and jitter > 0:
        delay = random.uniform(0, jitter)
        logger.info('Applying startup jitter: sleeping %.1fs', delay)
        time.sleep(delay)

    if not _acquire_lock(config):
        sys.exit(0)

    state = _load_state(config)
    cycle_start = time.time()
    stages = {}
    final_status = 'success'

    try:
        # Stage 1: updatedb (always)
        logger.info('Stage: updatedb')
        try:
            elapsed = _run_updatedb(config)
            stages['updatedb'] = {
                'status': 'success', 'elapsed_s': round(elapsed, 2)}
            logger.info('Stage updatedb completed in %.2fs', elapsed)
        except SystemExit as exc:
            stages['updatedb'] = {'status': 'failed', 'exit_code': exc.code}
            final_status = 'failed'
            logger.error('Stage updatedb exited with code %s', exc.code)
            raise

        # Stage 2: fetch event details (optional)
        if config.get('daemon_run_fetch_event', False):
            logger.info('Stage: fetch event details')
            try:
                elapsed = _run_fetch_event(config)
                stages['fetch_event'] = {
                    'status': 'success', 'elapsed_s': round(elapsed, 2)
                }
                logger.info(
                    'Stage fetch_event completed in %.2fs', elapsed
                )
            except SystemExit as exc:
                stages['fetch_event'] = {
                    'status': 'failed', 'exit_code': exc.code
                }
                final_status = 'partial'
                logger.error(
                    'Stage fetch_event exited with code %s', exc.code
                )

        # Stage 3: fetch waveform data (optional)
        if config.get('daemon_run_fetch_data', False):
            logger.info('Stage: fetch waveform data')
            try:
                elapsed = _run_fetch_data(config)
                stages['fetch_data'] = {
                    'status': 'success', 'elapsed_s': round(elapsed, 2)
                }
                logger.info(
                    'Stage fetch_data completed in %.2fs', elapsed
                )
            except SystemExit as exc:
                stages['fetch_data'] = {
                    'status': 'failed', 'exit_code': exc.code
                }
                if final_status == 'success':
                    final_status = 'partial'
                logger.error(
                    'Stage fetch_data exited with code %s', exc.code
                )

    except SystemExit:
        # Already logged above; persist state before re-raising
        _persist_and_release(config, state, cycle_start, stages, final_status)
        raise
    except Exception as exc:  # noqa: BLE001
        final_status = 'failed'
        logger.exception('Unexpected error in daemon cycle: %s', exc)
        _persist_and_release(config, state, cycle_start, stages, final_status)
        sys.exit(1)

    _persist_and_release(config, state, cycle_start, stages, final_status)
    logger.info(
        '=== seiscat daemon cycle finished (status: %s) ===', final_status
    )
    if final_status == 'failed':
        sys.exit(1)


def _persist_and_release(config, state, cycle_start, stages, final_status):
    """Save state and release the lock."""
    from datetime import datetime, timezone
    state['last_run'] = {
        'started_at': datetime.fromtimestamp(
            cycle_start, tz=timezone.utc
        ).isoformat(),
        'status': final_status,
        'stages': stages,
    }
    try:
        _save_state(config, state)
    except Exception as exc:  # noqa: BLE001
        logger.warning('Could not save daemon state: %s', exc)
    _release_lock(config)

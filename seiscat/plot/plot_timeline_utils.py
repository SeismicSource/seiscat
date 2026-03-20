# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Common utility functions for timeline plotting.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import re
import numpy as np
from datetime import datetime, timezone

# time constants in seconds
ONE_MINUTE_SECONDS = 60.0
ONE_HOUR_SECONDS = 60 * ONE_MINUTE_SECONDS
ONE_DAY_SECONDS = 24 * ONE_HOUR_SECONDS
ONE_WEEK_SECONDS = 7 * ONE_DAY_SECONDS
AVERAGE_MONTH_DAYS = 30.4375
AVERAGE_YEAR_DAYS = 365.25
ONE_MONTH_SECONDS = AVERAGE_MONTH_DAYS * ONE_DAY_SECONDS
ONE_YEAR_SECONDS = AVERAGE_YEAR_DAYS * ONE_DAY_SECONDS


def _utcdatetime_to_datetime(utcdt):
    """Convert an obspy UTCDateTime to a timezone-aware Python datetime."""
    return datetime.fromtimestamp(float(utcdt), tz=timezone.utc)


def get_event_times_and_values(events, attribute):
    """
    Extract event times and the value of a given attribute.

    Events for which the attribute is missing or non-numeric are silently
    skipped.

    :param events: EventList of Event dicts
    :param attribute: name of the event attribute to extract
    :returns: list of (datetime, float) tuples, sorted by time
    """
    return [
        (dt, val)
        for dt, val, _event in get_event_times_values_and_events(
            events, attribute
        )
    ]


def get_event_times_values_and_events(events, attribute):
    """
    Extract event times, numeric attribute values, and source events.

    Events for which the attribute is missing or non-numeric are silently
    skipped.

    :param events: EventList of Event dicts
    :param attribute: name of the event attribute to extract
    :returns: list of (datetime, float, event) tuples, sorted by time
    """
    result = []
    for event in events:
        val = event.get(attribute)
        if val is None:
            continue
        try:
            val = float(val)
        except (ValueError, TypeError):
            continue
        if np.isnan(val):
            continue
        result.append((_utcdatetime_to_datetime(event['time']), val, event))
    result.sort(key=lambda x: x[0])
    return result


# ---------------------------------------------------------------------------
# Binning helpers
# ---------------------------------------------------------------------------

def _parse_bin_duration(spec):
    """
    Parse a bin-width specifier string into seconds.

    Accepted formats: ``Nd`` (days), ``Nw`` (weeks), ``Nm`` (months, ~30.4 d),
    ``Ny`` (years, ~365.25 d).  N may be a float.

    :param spec: string specifier, e.g. ``'7d'``, ``'1m'``, ``'0.5y'``
    :returns: duration in seconds, or ``None`` if the string is not recognised
    """
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([dwmy])$', spec.strip().lower())
    if m is None:
        return None
    value = float(m[1])
    unit = m[2]
    mapping = {
        'd': ONE_DAY_SECONDS,
        'w': ONE_WEEK_SECONDS,
        'm': ONE_MONTH_SECONDS,
        'y': ONE_YEAR_SECONDS,
    }
    return value * mapping[unit]


def _auto_bin_seconds(time_span_seconds):
    """
    Choose an appropriate bin width (in seconds) given the total time span.

    Rules:
    * span ≤ 1 week   → 1-hour bins
    * span ≤ 30 days  → 1-day bins
    * span ≤ 1 year   → 1-week bins
    * span ≤ 5 years  → 1-month bins (~30.4 d)
    * span > 5 years  → 1-year bins (~365.25 d)
    """
    if time_span_seconds <= ONE_WEEK_SECONDS:
        return ONE_HOUR_SECONDS
    if time_span_seconds <= 30 * ONE_DAY_SECONDS:
        return ONE_DAY_SECONDS
    if time_span_seconds <= ONE_YEAR_SECONDS:
        return ONE_WEEK_SECONDS
    # sourcery skip: reintroduce-else
    if time_span_seconds <= 5 * ONE_YEAR_SECONDS:
        return ONE_MONTH_SECONDS
    return ONE_YEAR_SECONDS


def bin_events_by_time(events, bins_spec=None):
    """
    Bin events into time intervals and count events in each bin.

    :param events: EventList of Event dicts
    :param bins_spec: bin specification.  One of:

        * ``None`` / ``'auto'``: automatic bin width
        * integer string (e.g. ``'20'``): that many equal-width bins
        * duration string (e.g. ``'7d'``, ``'1m'``): fixed bin width

    :returns: list of ``(bin_start, bin_end, count)`` tuples where
        *bin_start* and *bin_end* are timezone-aware datetimes and *count*
        is an ``int``.
    """
    if not events:
        return []

    times_dt = [_utcdatetime_to_datetime(e['time']) for e in events]
    times_ts = np.array([dt.timestamp() for dt in times_dt])
    t0_ts = times_ts.min()
    t1_ts = times_ts.max()
    total_span = t1_ts - t0_ts

    # --- resolve bin edges in timestamp (float seconds) ---
    if bins_spec is None or bins_spec == 'auto':
        bin_sec = (
            _auto_bin_seconds(total_span)
            if total_span > 0 else ONE_HOUR_SECONDS
        )
        n_bins = max(1, int(np.ceil(total_span / bin_sec)))
        edges = np.linspace(t0_ts, t0_ts + n_bins * bin_sec, n_bins + 1)
    else:
        # Try integer first
        try:
            n_bins = int(bins_spec)
            n_bins = max(n_bins, 1)
            edges = np.linspace(
                t0_ts,
                t1_ts if total_span > 0 else t0_ts + ONE_HOUR_SECONDS,
                n_bins + 1
            )
        except ValueError:
            bin_sec = _parse_bin_duration(bins_spec)
            if bin_sec is None:
                bin_sec = (
                    _auto_bin_seconds(total_span)
                    if total_span > 0 else ONE_HOUR_SECONDS
                )
            n_bins = max(1, int(np.ceil(total_span / bin_sec)))
            edges = np.linspace(t0_ts, t0_ts + n_bins * bin_sec, n_bins + 1)

    # Last edge must be strictly greater than the latest event so that the
    # rightmost event falls inside the last bin.
    if edges[-1] <= t1_ts:
        edges[-1] = t1_ts + 1.0

    counts, _ = np.histogram(times_ts, bins=edges)

    result = []
    for i, count in enumerate(counts):
        bin_start = datetime.fromtimestamp(edges[i], tz=timezone.utc)
        bin_end = datetime.fromtimestamp(edges[i + 1], tz=timezone.utc)
        result.append((bin_start, bin_end, int(count)))
    return result


def bin_label(bin_start, bin_end):
    """
    Return a short human-readable label for a time bin.

    The label format adapts to the bin width:
    * ≤ 2 days  → ``YYYY-MM-DD HH:MM``
    * ≤ 60 days → ``YYYY-MM-DD``
    * ≤ 400 days → ``YYYY-Www`` (ISO week)
    * otherwise  → ``YYYY-MM``
    """
    width_days = (bin_end - bin_start).total_seconds() / ONE_DAY_SECONDS
    if width_days <= 2:
        return bin_start.strftime('%Y-%m-%d %H:%M')
    if width_days <= 60:
        return bin_start.strftime('%Y-%m-%d')
    if width_days <= 400:
        return bin_start.strftime('%Y-%b')
    return bin_start.strftime('%Y')


def _seconds_to_human_duration(seconds):
    """Convert a duration in seconds to a compact human-readable string."""
    def _format_value(value):
        return f'{value:.1f}'.rstrip('0').rstrip('.')

    def _fmt(value, singular, plural):
        unit = singular if abs(value - 1.0) < 1e-9 else plural
        return f'{_format_value(value)} {unit}'

    if seconds < 2 * ONE_MINUTE_SECONDS:
        return _fmt(seconds, 'second', 'seconds')
    if seconds < 2 * ONE_HOUR_SECONDS:
        return _fmt(seconds / ONE_MINUTE_SECONDS, 'minute', 'minutes')
    if seconds < 2 * ONE_DAY_SECONDS:
        return _fmt(seconds / ONE_HOUR_SECONDS, 'hour', 'hours')
    if seconds < 60 * ONE_DAY_SECONDS:
        return _fmt(seconds / ONE_DAY_SECONDS, 'day', 'days')
    if seconds < 2 * ONE_YEAR_SECONDS:
        return _fmt(seconds / ONE_MONTH_SECONDS, 'month', 'months')
    return _fmt(seconds / ONE_YEAR_SECONDS, 'year', 'years')


def get_bin_size_label(bins, bins_spec=None):
    """
    Return a concise label describing the effective bin size.

    :param bins: list of ``(bin_start, bin_end, count)`` tuples
    :param bins_spec: user-provided bin spec from CLI
    :returns: string such as ``'auto, 7 days'`` or
        ``'20 bins, 7 days each'``
    """
    if not bins:
        return 'n/a'
    width_seconds = (bins[0][1] - bins[0][0]).total_seconds()
    width_human = _seconds_to_human_duration(width_seconds)

    if bins_spec is None or str(bins_spec).strip().lower() == 'auto':
        return f'auto, {width_human}'

    spec = str(bins_spec).strip()
    try:
        n_bins = int(spec)
    except ValueError:
        n_bins = None

    if n_bins is not None:
        return f'{n_bins} bins, {width_human} each'

    # duration-like custom spec, or any non-integer string that ended up
    # falling back to automatic binning.
    seconds = _parse_bin_duration(spec)
    if seconds is not None:
        return _seconds_to_human_duration(seconds)
    return f'{spec}, {width_human}'

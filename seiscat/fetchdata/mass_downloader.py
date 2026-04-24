# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Uses ObsPy mass downloader to download event waveforms from FDSN web services.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import sys
import pathlib
import logging
import shutil
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.mass_downloader import (
    CircularDomain, Restrictions, MassDownloader
)
from .event_waveforms_utils import (
    prefer_high_sampling_rate,
    get_event_layout_paths,
    get_event_xml_file,
    bundle_waveforms_to_mseed,
    bundle_stations_to_xml,
)
from ..utils import ExceptionExit
mdl_logger = logging.getLogger('obspy.clients.fdsn.mass_downloader')


def _parse_magnitude_bins(magnitude, station_radius_max_mag):
    """
    Parse magnitude bins and calculate radius using discrete binning.

    Uses the radius from the largest bin magnitude that doesn't exceed
    the event magnitude.

    :param magnitude: Event magnitude
    :param station_radius_max_mag: String with format
        "mag1: radius1, mag2: radius2, ..."
    :return: Calculated radius
    :raises ValueError: If parsing fails
    :raises IndexError: If parsing fails
    """
    # Parse magnitude bins
    bins = [
        (float(mag_str.strip()), float(rad_str.strip()))
        for pair in station_radius_max_mag.split(',')
        for mag_str, rad_str in [pair.split(':')]
    ]
    # Sort bins by magnitude
    bins.sort(key=lambda x: x[0])
    # Find the appropriate radius using discrete binning
    # Use the radius from the largest bin magnitude that doesn't exceed
    # the event magnitude
    radius = bins[0][1]  # Default to first bin
    for mag_bin, rad_bin in bins:
        if magnitude >= mag_bin:
            radius = rad_bin
        else:
            break
    return radius


def _evaluate_magnitude_expression(magnitude, station_radius_max_mag):
    """
    Evaluate a mathematical expression to calculate radius.

    :param magnitude: Event magnitude
    :param station_radius_max_mag: Mathematical expression string
        (e.g., "2.0 * mag - 3.0")
    :return: Calculated radius
    :raises ValueError: If expression is invalid
    :raises Exception: If evaluation fails
    """
    # Create a safe namespace with only allowed operations
    safe_dict = {
        'mag': magnitude,
        '__builtins__': {},
        'abs': abs,
        'min': min,
        'max': max,
        'pow': pow,
    }
    # Evaluate the expression
    # pylint: disable=eval-used
    radius = eval(station_radius_max_mag, safe_dict)
    if not isinstance(radius, (int, float)):
        raise ValueError('Expression must evaluate to a number')
    return radius


def _calculate_station_radius_max(
        magnitude, station_radius_max_mag, station_radius_min,
        station_radius_max):
    """
    Calculate the magnitude-dependent maximum station radius.

    :param magnitude: Event magnitude
    :param station_radius_max_mag: Configuration string for
        magnitude-dependent radius. Can be either:
        - Magnitude bins (discrete): "mag1: radius1, mag2: radius2, ..."
        - Mathematical expression: "2.0 * mag - 3.0"
    :param station_radius_min: Minimum station radius (lower bound)
    :param station_radius_max: Maximum station radius (upper bound)
    :return: Calculated radius, bounded by station_radius_min and
        station_radius_max
    """
    if station_radius_max_mag is None:
        return station_radius_max
    # Try to parse as magnitude bins first
    # (format: "mag1: radius1, mag2: radius2, ...")
    if ':' in station_radius_max_mag:
        try:
            radius = _parse_magnitude_bins(
                magnitude, station_radius_max_mag)
        except (ValueError, IndexError) as e:
            mdl_logger.warning(
                'Failed to parse station_radius_max_mag as bins: %s. '
                'Using default station_radius_max.', e
            )
            return station_radius_max
    else:
        # Try to parse as mathematical expression
        try:
            radius = _evaluate_magnitude_expression(
                magnitude, station_radius_max_mag)
        except Exception as e:  # pylint: disable=broad-except
            mdl_logger.warning(
                'Failed to evaluate station_radius_max_mag expression: '
                '%s. Using default station_radius_max.', e
            )
            return station_radius_max
    # Apply bounds
    radius = max(station_radius_min, min(radius, station_radius_max))
    return radius


def _build_providers(config):
    """
    Build the providers list for MassDownloader.

    If credentials are configured, returns a list of Client objects.
    Otherwise returns the raw providers list (strings or None).

    :param config: config object
    :returns: list of Client objects, list of strings, or None
    """
    providers = config['fdsn_providers']
    users = config.get('fdsn_providers_users')
    passwords = config.get('fdsn_providers_passwords')
    if providers is None or (users is None and passwords is None):
        return providers
    # Pad credential lists with None to match providers length
    n = len(providers)
    users = list(users or []) + [None] * n
    passwords = list(passwords or []) + [None] * n
    clients = []
    for i, provider in enumerate(providers):
        user = users[i] if users[i] != 'None' else None
        password = passwords[i] if passwords[i] != 'None' else None
        kwargs = {}
        if user is not None:
            kwargs['user'] = user
        if password is not None:
            kwargs['password'] = password
        clients.append(Client(provider, **kwargs))
    return clients


def _check_fdsn_providers(fdsn_providers):
    """
    Check if the user wants to use all known FDSN providers.

    Exit if the user does not want to use any provider.

    :param providers: list of FDSN providers or None
    """
    if fdsn_providers is not None:
        return
    print(
        'No FDSN providers set in config file. Do you want to use all '
        'known providers? (y/N)', end=' '
    )
    while True:
        answer = input().strip().lower()
        if answer in ('y', 'yes'):
            break
        if answer in ('n', 'no', ''):
            print('Exiting.')
            sys.exit()
        print('Please answer y or n:', end=' ')


def _set_mdl_logger(evid):
    """
    Set up the ObsPy mass downloader logger.
    Prepend the event ID to each log message.

    :param evid: event ID
    """
    mdl_logger.setLevel(logging.DEBUG)
    # Prevent propagating to higher loggers.
    mdl_logger.propagate = 0
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(f'{evid}: %(message)s'))
    handler.setLevel(logging.INFO)
    mdl_logger.addHandler(handler)


def _unset_mdl_logger():
    """
    Unset the ObsPy mass downloader logger.
    """
    mdl_logger.handlers = []


def _log_no_station_match_and_return_zero():
    """Log no-match condition, clean up logger state, and return 0."""
    mdl_logger.info('No stations match the selection criteria.')
    _unset_mdl_logger()
    return 0


def _build_station_restriction(
        evid_dir, evid, station_codes, picked_stations_only):
    """
    Build the station restriction for the mass downloader.

    Returns a set of station codes to restrict the download to, a raw
    station codes string, or None (no restriction).

    If ``picked_stations_only`` is True, reads the event QuakeML file and
    extracts stations with P or S-wave picks.  If ``station_codes`` is also
    provided, the result is further filtered to only include stations that
    match ``station_codes``.

    :param evid_dir: path to the event directory
    :param evid: event ID
    :param station_codes: station codes string (comma-separated, may contain
        wildcards), or None
    :param picked_stations_only: if True, restrict to stations with picks
    :returns: set of station codes, raw station-codes string, or None
    """
    from .event_waveforms_utils import check_station, get_picked_station_codes
    if not picked_stations_only and not station_codes:
        return None
    if picked_stations_only:
        picked = get_picked_station_codes(evid_dir, evid)
        if picked is None:
            event_xml = get_event_xml_file(evid_dir, evid)
            if event_xml is None:
                event_xml = pathlib.Path(evid_dir) / f'{evid}.xml'
            mdl_logger.warning(
                'picked_stations_only is True but no event QuakeML file '
                'found at %s. Ignoring pick-based station selection.',
                event_xml
            )
            # Fall through to plain station_codes restriction (or None)
            if not station_codes:
                return None
        else:
            if not picked:
                mdl_logger.warning(
                    'No P/S picks found in the event QuakeML file. '
                    'No waveforms will be downloaded.'
                )
                return set()  # empty set → no stations
            mdl_logger.info(
                'Restricting download to %d station(s) with picks: %s',
                len(picked), ', '.join(sorted(picked))
            )
            if station_codes:
                # Further filter picked stations by station_codes pattern
                picked = {
                    sta for sta in picked
                    if check_station(sta, station_codes)
                }
                if not picked:
                    mdl_logger.warning(
                        'No picked stations match station_codes "%s". '
                        'No waveforms will be downloaded.', station_codes
                    )
                    return set()  # empty set → no stations
                mdl_logger.info(
                    'After applying station_codes filter: %d station(s): %s',
                    len(picked), ', '.join(sorted(picked))
                )
            return picked
    # Only station_codes (no picked_stations_only)
    return station_codes.replace(' ', '')


def _split_network_station_codes(station_codes):
    """
    Split station code patterns into network and station restrictions.

    Supports station-only tokens (e.g., ``ABC*``) and network-qualified tokens
    (e.g., ``FR.ABC*``). If at least one qualified token is present, returns
    both network and station comma-separated patterns for MassDownloader
    restrictions.

    :param station_codes: comma-separated station patterns
    :returns: (network_patterns_or_none, station_patterns)
    """
    tokens = [tok.strip() for tok in station_codes.split(',') if tok.strip()]
    if all('.' not in tok for tok in tokens):
        return None, ','.join(tokens)
    networks = []
    stations = []
    for tok in tokens:
        net, sta = tok.split('.', 1) if '.' in tok else ('*', tok)
        networks.append(net)
        stations.append(sta)
    network_codes = ','.join(dict.fromkeys(networks))
    station_patterns = ','.join(dict.fromkeys(stations))
    return network_codes, station_patterns


def mass_download_waveforms(config, event):
    """
    Download waveforms for a single event using ObsPy mass downloader.

    :param config: config object
    :param event: event object
    :returns: number of station metadata files downloaded for this event
    """
    _check_fdsn_providers(config['fdsn_providers'])
    evid = event['evid']
    latitude = event['lat']
    longitude = event['lon']
    magnitude = event['mag']
    origin_time = event['time']
    providers = _build_providers(config)
    station_radius_min = config['station_radius_min']
    station_radius_max = config['station_radius_max']
    station_radius_max_mag = config.get('station_radius_max_mag', None)
    seconds_before = config['seconds_before_origin']
    seconds_after = config['seconds_after_origin']
    duration_min = config['duration_min']
    interstation_distance_min = config['interstation_distance_min']
    channel_codes = config['channel_codes']
    station_codes = config['station_codes']
    picked_stations_only = config['picked_stations_only']
    paths = get_event_layout_paths(config, evid)
    evid_dir = paths['evid_dir']
    waveform_dir = pathlib.Path(paths['waveform_dir'])
    waveform_dir.mkdir(parents=True, exist_ok=True)
    station_dir = pathlib.Path(paths['station_dir'])
    station_dir.mkdir(parents=True, exist_ok=True)

    _set_mdl_logger(evid)
    mdl_logger.info('Downloading waveforms and station metadata')
    # Calculate magnitude-dependent radius if configured
    if station_radius_max_mag is not None and magnitude is not None:
        station_radius_max = _calculate_station_radius_max(
            magnitude, station_radius_max_mag,
            station_radius_min, station_radius_max
        )
        mdl_logger.info(
            'Using magnitude-dependent station radius: '
            '%.2f° (magnitude=%.2f)', station_radius_max, magnitude
        )
    domain = CircularDomain(
        latitude=latitude, longitude=longitude,
        minradius=station_radius_min, maxradius=station_radius_max
    )
    restrictions = {
        'starttime': origin_time - seconds_before,
        'endtime': origin_time + seconds_after,
        'reject_channels_with_gaps': False,
        'minimum_length': duration_min,
        'minimum_interstation_distance_in_m': (
            interstation_distance_min * 1e3
        ),
    }
    if channel_codes:
        # remove spaces inside channel codes
        channel_codes = channel_codes.replace(' ', '')
        restrictions['channel'] = channel_codes
    else:
        restrictions['channel'] = '*'
    # Build station restriction
    station_restriction = _build_station_restriction(
        evid_dir, evid, station_codes, picked_stations_only)
    if station_restriction is not None:
        if not station_restriction:
            # Empty set: no stations to download
            return _log_no_station_match_and_return_zero()
        if isinstance(station_restriction, set):
            restrictions['station'] = ','.join(station_restriction)
        else:
            network_codes, station_patterns = _split_network_station_codes(
                station_restriction)
            restrictions['station'] = station_patterns
            if network_codes is not None:
                restrictions['network'] = network_codes
    restrictions = Restrictions(**restrictions)
    with ExceptionExit():
        mdl = MassDownloader(providers=providers, configure_logging=False)
        mdl.download(
            domain, restrictions,
            mseed_storage=str(waveform_dir),
            stationxml_storage=str(station_dir)
        )
    n_stations = len(list(station_dir.glob('*.xml')))
    if config['prefer_high_sampling_rate']:
        prefer_high_sampling_rate(waveform_dir, mdl_logger)
    if paths['layout'] == 'event_files':
        waveforms_written = bundle_waveforms_to_mseed(
            waveform_dir, paths['waveform_file'])
        stations_written = bundle_stations_to_xml(
            station_dir, paths['station_file'])
        shutil.rmtree(waveform_dir, ignore_errors=True)
        shutil.rmtree(station_dir, ignore_errors=True)
        if waveforms_written:
            mdl_logger.info(
                'Bundled waveforms saved to %s',
                paths['waveform_file']
            )
        if stations_written:
            mdl_logger.info(
                'Bundled stations saved to %s',
                paths['station_file']
            )
    _info_msg = f'Waveforms and station metadata saved to {evid_dir}'
    mdl_logger.info(_info_msg)
    _unset_mdl_logger()
    return n_stations

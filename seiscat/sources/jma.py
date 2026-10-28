# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Read an event catalog in the JMA hypocenter data format.

The Japan Meteorological Agency (JMA) distributes its earthquake catalog
(the "hypocenter data" files ``hYYYY`` of the JMA bulletin) as fixed-width
text records of 96 characters each. The format has no header and no
delimiter, hence it cannot be parsed as CSV or by ObsPy.

Format specification:
https://www.data.jma.go.jp/eqev/data/bulletin/data/format/hypfmt_e.html

Notable features of the format handled by this reader:

- origin times are given in Japan Standard Time (JST, UTC+9) and are
  converted to UTC;
- latitudes and longitudes are given as degrees plus minutes (the degrees
  field may be negative);
- depths are in km, either as a 5-character fixed-point number with 2
  implied decimals (depth-free method) or as an integer in the first 3
  characters (depth-slice and fixed-depth methods);
- magnitudes have 1 implied decimal digit and use letter codes for values
  below -0.9: ``-1`` = -0.1, ``-9`` = -0.9, ``A0`` = -1.0, ``A9`` = -1.9,
  ``B0`` = -2.0, ``C0`` = -3.0;
- events without a JMA event ID are assigned an ID generated from the
  origin time (see :func:`seiscat.sources.evid.generate_evid`).

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import re
from obspy import UTCDateTime
from obspy.core.event import (
    Catalog, CreationInfo, Event, Magnitude, Origin, OriginQuality)
from ..utils import int_or_none
from .evid import generate_evid

JMA_HYPOCENTER_FORMAT_URL =\
    'https://www.data.jma.go.jp/eqev/data/bulletin/data/format/hypfmt_e.html'

# Length of a JMA hypocenter record (characters)
JMA_RECORD_LENGTH = 96

# JMA origin times are in Japan Standard Time (UTC+9)
JMA_UTC_OFFSET = 9 * 3600

# Record type identifier (column 1) --> agency name
JMA_AGENCIES = {
    'J': 'JMA',
    'U': 'USGS',
    'I': 'International agency',
}

# Magnitude type (columns 55 and 58) --> ObsPy magnitude type
JMA_MAGNITUDE_TYPES = {
    'J': 'mjma',
    'D': 'md',
    'd': 'md',
    'V': 'mv',
    'v': 'mv',
    'W': 'mw',
    'B': 'mb',
    'S': 'ms',
}

# Subsidiary information (column 61) --> ObsPy event type
JMA_EVENT_TYPES = {
    '1': 'earthquake',              # natural earthquake
    '2': 'earthquake',              # insufficient number of JMA stations
    '3': 'anthropogenic event',     # artificial event
    '4': 'volcanic eruption',       # eruption earthquake and others
    '5': 'earthquake',              # low-frequency earthquake
}

# Fixed-width columns of a JMA hypocenter record, as Python slices
# (the format specification uses 1-based, inclusive column numbers)
COL_AGENCY = slice(0, 1)
COL_YEAR = slice(1, 5)
COL_MONTH = slice(5, 7)
COL_DAY = slice(7, 9)
COL_HOUR = slice(9, 11)
COL_MINUTE = slice(11, 13)
COL_SECOND = slice(13, 17)
COL_TIME_ERROR = slice(17, 21)
COL_LAT_DEG = slice(21, 24)
COL_LAT_MIN = slice(24, 28)
COL_LAT_ERROR = slice(28, 32)
COL_LON_DEG = slice(32, 36)
COL_LON_MIN = slice(36, 40)
COL_LON_ERROR = slice(40, 44)
COL_DEPTH = slice(44, 49)
COL_DEPTH_ERROR = slice(49, 52)
COL_MAG1 = slice(52, 54)
COL_MAG1_TYPE = slice(54, 55)
COL_MAG2 = slice(55, 57)
COL_MAG2_TYPE = slice(57, 58)
COL_TRAVEL_TIME_TABLE = slice(58, 59)
COL_PRECISION = slice(59, 60)
COL_SUBSIDIARY = slice(60, 61)
COL_MAX_INTENSITY = slice(61, 62)
COL_DAMAGE_CLASS = slice(62, 63)
COL_TSUNAMI_CLASS = slice(63, 64)
COL_DISTRICT = slice(64, 65)
COL_REGION_NUMBER = slice(65, 68)
COL_REGION_NAME = slice(68, 92)
COL_STATION_COUNT = slice(92, 95)
COL_FLAG = slice(95, 96)

# Minimum number of characters needed to read origin time, coordinates,
# depth and the first magnitude
_JMA_MIN_RECORD_LENGTH = 55

# Record type identifier followed by year, month, day, hour, minute,
# and seconds
_JMA_RECORD_RE = re.compile(r'^[JUI]\d{14}')


def _parse_fixed_decimal(field, n_decimals):
    """
    Parse a fixed-point field with an implied decimal separator.

    Fields like ``0458`` are read as ``4.58`` (2 implied decimals).
    When the decimal part is blank (e.g. fixed hypocenters, which are
    written as ``04  ``), the field is read as an integer.

    :param field: the field to parse
    :type field: str
    :param n_decimals: number of implied decimal digits
    :type n_decimals: int

    :return: the parsed value, or None if the field is blank
    :rtype: float or None
    """
    if not field.strip():
        return None
    if field[-n_decimals:].strip() == '':
        # blank decimal part: integer value
        return float(field.strip())
    try:
        return int(field) / 10 ** n_decimals
    except ValueError:
        # a field with an explicit decimal separator
        try:
            return float(field)
        except ValueError:
            return None


def _parse_degrees(field):
    """
    Parse a degrees field.

    The sign may be separated from the digits by blanks (e.g. ``- 5``),
    as used for single-digit degrees in the southern hemisphere or west
    of the Greenwich meridian.

    :param field: the degrees field
    :type field: str

    :return: the signed number of degrees, or None if it cannot be parsed
    :rtype: int or None
    """
    text = field.strip()
    sign = -1 if text.startswith('-') else 1
    degrees = int_or_none(text.lstrip('+-').strip())
    if degrees is None:
        return None
    return sign * abs(degrees)


def _parse_angle(degrees_field, minutes_field):
    """
    Parse an angle given as degrees plus minutes.

    :param degrees_field: the degrees field (may be negative)
    :type degrees_field: str
    :param minutes_field: the minutes field, with 2 implied decimals
    :type minutes_field: str

    :return: the angle in decimal degrees, or None if it cannot be parsed
    :rtype: float or None
    """
    text = degrees_field.strip()
    degrees = _parse_degrees(degrees_field)
    if degrees is None:
        return None
    minutes = _parse_fixed_decimal(minutes_field, 2)
    if minutes is None:
        minutes = 0.0
    sign = -1.0 if text.startswith('-') else 1.0
    return sign * (abs(degrees) + minutes / 60.0)


def _parse_depth(field):
    """
    Parse the depth field.

    The depth is either a 5-character fixed-point number with 2 implied
    decimals (depth-free method, e.g. `` 3621`` = 36.21 km) or an integer
    in the first 3 characters, followed by 2 blank characters
    (depth-slice and fixed-depth methods, e.g. `` 30  `` = 30 km).

    :param field: the depth field
    :type field: str

    :return: the depth in km, or None if it cannot be parsed
    :rtype: float or None
    """
    if not field.strip():
        return None
    if len(field) >= 5 and not field[3:5].strip():
        depth = int_or_none(field[:3])
        return None if depth is None else float(depth)
    return _parse_fixed_decimal(field[:5], 2)


def _parse_magnitude(field):
    """
    Parse a magnitude field.

    Magnitudes have 1 implied decimal digit. Values below -0.9 are coded
    with letters: ``-1`` = -0.1, ``-9`` = -0.9, ``A0`` = -1.0, ``A9`` =
    -1.9, ``B0`` = -2.0, ``C0`` = -3.0.

    :param field: the magnitude field
    :type field: str

    :return: the magnitude, or None if the field is blank
    :rtype: float or None
    """
    text = field.strip()
    if not text:
        return None
    if text[0] in 'ABC':
        try:
            return -(ord(text[0]) - ord('A') + 1) - int(text[1:]) / 10.0
        except ValueError:
            return None
    try:
        return int(text) / 10.0
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def _parse_magnitude_type(code):
    """
    Convert a JMA magnitude type code to an ObsPy magnitude type.

    :param code: the JMA magnitude type code (one character)
    :type code: str

    :return: the magnitude type, or None if undetermined
    :rtype: str or None
    """
    return JMA_MAGNITUDE_TYPES.get(code.strip())


def _extra_value(value):
    """
    Format a value to be stored in the event ``extra`` dictionary.

    :param value: the value to store
    :type value: str, int, float or None

    :return: a seiscat extra field dictionary, or None for blank values
    :rtype: dict or None
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    return {'value': value, 'namespace': 'seiscat'}


def _read_origin_time(line):
    """
    Read the origin time from a JMA hypocenter record.

    The origin time is converted from JST to UTC.

    :param line: the JMA hypocenter record
    :type line: str

    :return: the origin time in UTC
    :rtype: obspy.UTCDateTime

    :raises ValueError: if the origin time cannot be parsed
    """
    year = int_or_none(line[COL_YEAR])
    month = int_or_none(line[COL_MONTH])
    day = int_or_none(line[COL_DAY])
    hour = int_or_none(line[COL_HOUR])
    minute = int_or_none(line[COL_MINUTE])
    second = _parse_fixed_decimal(line[COL_SECOND], 2)
    if None in (year, month, day, hour, minute, second):
        raise ValueError('cannot parse origin time')
    # UTCDateTime does not accept a float number of seconds on all
    # supported ObsPy versions, so add the fractional part separately
    second, fraction = divmod(round(second, 2), 1)
    try:
        orig_time = UTCDateTime(
            year=year, month=month, day=day,
            hour=hour, minute=minute, second=int(second)
        )
    except (ValueError, TypeError) as e:
        raise ValueError(f'cannot parse origin time: {e}') from e
    # JMA origin times are in JST (UTC+9)
    return orig_time + fraction - JMA_UTC_OFFSET


def _read_jma_record(line):
    """
    Read a single JMA hypocenter record.

    :param line: a JMA hypocenter record
    :type line: str

    :return: an ObsPy event object
    :rtype: obspy.Event

    :raises ValueError: if the record cannot be parsed
    """
    # pad short records (e.g. trailing blanks stripped by an editor)
    line = line.rstrip('\n').rstrip('\r')
    line = line.ljust(JMA_RECORD_LENGTH)
    if not _JMA_RECORD_RE.match(line):
        raise ValueError('not a JMA hypocenter record')
    orig_time = _read_origin_time(line)
    ev = Event()
    ev.resource_id = generate_evid(orig_time)
    subsidiary = line[COL_SUBSIDIARY].strip()
    if subsidiary in JMA_EVENT_TYPES:
        ev.event_type = JMA_EVENT_TYPES[subsidiary]
    agency = JMA_AGENCIES.get(line[COL_AGENCY].strip())
    if agency is not None:
        ev.creation_info = CreationInfo(agency_id=agency)
    orig = Origin()
    orig.time = orig_time
    orig.latitude = _parse_angle(line[COL_LAT_DEG], line[COL_LAT_MIN])
    orig.longitude = _parse_angle(line[COL_LON_DEG], line[COL_LON_MIN])
    depth = _parse_depth(line[COL_DEPTH])
    # seiscat stores depths in meters
    orig.depth = None if depth is None else depth * 1000.0
    quality = OriginQuality()
    time_error = _parse_fixed_decimal(line[COL_TIME_ERROR], 2)
    if time_error is not None:
        quality.standard_error = time_error
    station_count = int_or_none(line[COL_STATION_COUNT])
    if station_count is not None:
        quality.associated_station_count = station_count
    orig.quality = quality
    ev.origins.append(orig)
    ev.preferred_origin_id = orig.resource_id
    # use the first magnitude, unless it is missing
    mag = Magnitude()
    magnitude = _parse_magnitude(line[COL_MAG1])
    magnitude_type = _parse_magnitude_type(line[COL_MAG1_TYPE])
    if magnitude is None:
        magnitude = _parse_magnitude(line[COL_MAG2])
        magnitude_type = _parse_magnitude_type(line[COL_MAG2_TYPE])
    mag.mag = magnitude
    mag.magnitude_type = magnitude_type
    ev.magnitudes.append(mag)
    ev.preferred_magnitude_id = mag.resource_id
    # store the JMA-specific information as event extra fields
    ev.extra = {
        'jma_agency': _extra_value(agency),
        'jma_region': _extra_value(line[COL_REGION_NAME]),
        'jma_region_number': _extra_value(
            int_or_none(line[COL_REGION_NUMBER])),
        'jma_district_number': _extra_value(
            int_or_none(line[COL_DISTRICT])),
        'jma_station_count': _extra_value(station_count),
        'jma_determination_flag': _extra_value(line[COL_FLAG]),
        'jma_precision': _extra_value(line[COL_PRECISION]),
        'jma_travel_time_table': _extra_value(line[COL_TRAVEL_TIME_TABLE]),
        'jma_subsidiary': _extra_value(subsidiary),
        'jma_max_intensity': _extra_value(line[COL_MAX_INTENSITY]),
        'jma_damage_class': _extra_value(line[COL_DAMAGE_CLASS]),
        'jma_tsunami_class': _extra_value(line[COL_TSUNAMI_CLASS]),
    }
    ev.extra = {
        key: value for key, value in ev.extra.items() if value is not None
    }
    return ev


def _looks_like_jma_record(line):
    """
    Check if a line looks like a JMA hypocenter record.

    :param line: the line to check
    :type line: str

    :return: True if the line looks like a JMA hypocenter record
    :rtype: bool
    """
    line = line.rstrip('\n').rstrip('\r')
    if not _JMA_MIN_RECORD_LENGTH <= len(line) <= JMA_RECORD_LENGTH:
        return False
    if not _JMA_RECORD_RE.match(line):
        return False
    # latitude and longitude degrees must be integers
    return (
        _parse_degrees(line[COL_LAT_DEG]) is not None
        and _parse_degrees(line[COL_LON_DEG]) is not None
    )


def is_jma_hypocenter_file(filename, max_lines=10):
    """
    Check if a file is in the JMA hypocenter data format.

    The check is performed on the first non-empty lines of the file.

    :param filename: input filename
    :type filename: str
    :param max_lines: maximum number of lines to check
    :type max_lines: int

    :return: True if the file appears to be in the JMA hypocenter format
    :rtype: bool
    """
    n = 0
    try:
        with open(filename, 'r', encoding='utf8', errors='replace') as fp:
            for line in fp:
                if not line.strip():
                    continue
                if not _looks_like_jma_record(line):
                    return False
                n += 1
                if n >= max_lines:
                    break
    except OSError:
        return False
    return n > 0


def _count_records(filename):
    """
    Count the non-empty records in a JMA hypocenter file.

    :param filename: input filename
    :type filename: str

    :return: the number of records
    :rtype: int
    """
    nrecords = 0
    with open(filename, 'r', encoding='utf8', errors='replace') as fp:
        for line in fp:
            if line.strip():
                nrecords += 1
    return nrecords


def read_catalog_from_jma(config, filename=None):
    """
    Read a catalog from a file in the JMA hypocenter data format.

    The JMA hypocenter format (``hYYYY`` files of the JMA bulletin) is a
    fixed-width text format, described at
    https://www.data.jma.go.jp/eqev/data/bulletin/data/format/hypfmt_e.html

    :param config: configuration object
    :type config: dict
    :param filename: JMA filename (if None, uses args.fromfile[0])
    :type filename: str or None

    :return: an ObsPy catalog object
    :rtype: obspy.Catalog

    :raises FileNotFoundError: if filename does not exist
    :raises ValueError: if the file is not in the JMA hypocenter format
    """
    args = config['args']
    jma_filename = filename if filename is not None else args.fromfile[0]
    try:
        with open(jma_filename, 'r', encoding='utf8'):
            pass
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f'JMA file not found: {jma_filename}'
        ) from e
    if not is_jma_hypocenter_file(jma_filename):
        raise ValueError(
            f'File {jma_filename} does not appear to be in the JMA '
            'hypocenter format'
        )
    nrecords = _count_records(jma_filename)
    print(f'JMA hypocenter format: {nrecords} records')
    depth_units = getattr(args, 'depth_units', None)
    if depth_units is not None:
        print(
            'Note: --depth_units is ignored for the JMA hypocenter format '
            '(depths are in km)'
        )
    cat = Catalog()
    used_evids = {}
    with open(jma_filename, 'r', encoding='utf8', errors='replace') as fp:
        n = 0
        for line in fp:
            if not line.strip():
                continue
            n += 1
            print(f'reading record {n}/{nrecords}\r', end='')
            try:
                ev = _read_jma_record(line)
            except (ValueError, TypeError) as e:
                print(f'Error at record {n}: {e}')
                continue
            # make sure that events sharing the same origin time
            # (and thus the same generated evid) get a unique evid
            evid = str(ev.resource_id.id)
            if evid in used_evids:
                used_evids[evid] += 1
                evid = f'{evid}-{used_evids[evid]}'
                ev.resource_id = evid
            else:
                used_evids[evid] = 1
            cat.append(ev)
    print()  # needed to add a newline after the last "reading record" message
    return cat

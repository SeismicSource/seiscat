# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Unit tests for CSV reader module.

:copyright:
    2021-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch
from io import StringIO
from obspy import UTCDateTime
from obspy.core.event import Catalog, Event
from seiscat.sources.csv import (
    _field_match_score,
    _remove_redundant_fields,
    _guess_field_names,
    _csv_file_info,
    _read_orig_time_from_ymdhms,
    _split_date_time,
    _normalize_date_format,
    _read_orig_time_from_datetime,
    _read_orig_time_from_row,
    _read_csv_row,
    _read_csv,
    read_catalog_from_csv,
)


def create_mock_config(
    filename, depth_units='km', delimiter=None, column_names=None
):
    """Create a mock config object for testing.

    :param filename: CSV filename
    :type filename: str
    :param depth_units: depth units (km, m, or None)
    :type depth_units: str or None
    :param delimiter: CSV delimiter
    :type delimiter: str or None
    :param column_names: list of column names
    :type column_names: list or None

    :return: mock config dictionary
    :rtype: dict
    """
    args = MagicMock()
    args.fromfile = [filename]
    args.depth_units = depth_units
    args.delimiter = delimiter
    args.column_names = column_names
    return {'args': args}


class TestFieldMatchScore(unittest.TestCase):
    """Test _field_match_score function."""

    def test_perfect_match(self):
        """Test perfect match returns high score."""
        score = _field_match_score('latitude', ['latitude', 'longitude'])
        self.assertEqual(score, 999)

    def test_perfect_match_case_insensitive(self):
        """Test perfect match is case insensitive."""
        score = _field_match_score('Latitude', ['latitude', 'longitude'])
        self.assertEqual(score, 999)

    def test_partial_match(self):
        """Test partial match returns substring length."""
        score = _field_match_score('origin_latitude', ['lat'])
        self.assertEqual(score, 3)

    def test_no_match(self):
        """Test no match returns zero."""
        score = _field_match_score('timestamp', ['latitude', 'longitude'])
        self.assertEqual(score, 0)

    def test_longest_substring(self):
        """Test returns longest matching substring."""
        score = _field_match_score('origin_time', ['time', 'origin'])
        self.assertEqual(score, 6)  # 'origin' is longer than 'time'


class TestRemoveRedundantFields(unittest.TestCase):
    """Test _remove_redundant_fields function."""

    def test_removes_redundant_fields(self):
        """Test redundant fields are removed when main field exists."""
        output_fields = {
            'date': 'DATE',
            'year': 'YEAR',
            'month': 'MONTH',
            'day': 'DAY'
        }
        _remove_redundant_fields(
            output_fields, 'date', ['year', 'month', 'day']
        )
        self.assertEqual(output_fields['date'], 'DATE')
        self.assertIsNone(output_fields['year'])
        self.assertIsNone(output_fields['month'])
        self.assertIsNone(output_fields['day'])

    def test_keeps_redundant_fields_when_main_none(self):
        """Test redundant fields are kept when main field is None."""
        output_fields = {
            'date': None,
            'year': 'YEAR',
            'month': 'MONTH',
            'day': 'DAY'
        }
        _remove_redundant_fields(
            output_fields, 'date', ['year', 'month', 'day']
        )
        self.assertIsNone(output_fields['date'])
        self.assertEqual(output_fields['year'], 'YEAR')
        self.assertEqual(output_fields['month'], 'MONTH')
        self.assertEqual(output_fields['day'], 'DAY')


class TestGuessFieldNames(unittest.TestCase):
    """Test _guess_field_names function."""

    def test_identifies_standard_fields(self):
        """Test identification of standard field names."""
        input_fields = ['latitude', 'longitude', 'depth', 'magnitude', 'time']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        self.assertEqual(fields['lat'], 'latitude')
        self.assertEqual(fields['lon'], 'longitude')
        self.assertEqual(fields['depth'], 'depth')
        self.assertEqual(fields['mag'], 'magnitude')
        self.assertEqual(fields['time'], 'time')

    def test_identifies_abbreviated_fields(self):
        """Test identification of abbreviated field names."""
        input_fields = ['lat', 'lon', 'dep', 'mag', 'datetime']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        self.assertEqual(fields['lat'], 'lat')
        self.assertEqual(fields['lon'], 'lon')
        self.assertEqual(fields['depth'], 'dep')
        self.assertEqual(fields['mag'], 'mag')
        self.assertEqual(fields['time'], 'datetime')

    def test_identifies_date_time_components(self):
        """Test identification of separate date-time components."""
        input_fields = ['year', 'month', 'day', 'hour', 'minute', 'seconds']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        self.assertEqual(fields['year'], 'year')
        self.assertEqual(fields['month'], 'month')
        self.assertEqual(fields['day'], 'day')
        self.assertEqual(fields['hour'], 'hour')
        self.assertEqual(fields['minute'], 'minute')
        self.assertEqual(fields['seconds'], 'seconds')

    def test_raises_error_when_no_fields_identified(self):
        """Test raises ValueError when no fields can be identified."""
        input_fields = ['unknown1', 'unknown2', 'unknown3']
        with patch('builtins.print'):
            with self.assertRaises(ValueError):
                _guess_field_names(input_fields)

    def test_raises_error_for_incomplete_datetime_components(self):
        """Test raises error for incomplete datetime components."""
        input_fields = ['year', 'month', 'latitude', 'longitude']
        with patch('builtins.print'):
            with self.assertRaises(ValueError):
                _guess_field_names(input_fields)

    def test_removes_date_redundancy(self):
        """Test removes year/month/day when date field present."""
        input_fields = ['date', 'time', 'year', 'month', 'day', 'latitude']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        self.assertEqual(fields['date'], 'date')
        self.assertEqual(fields['time'], 'time')
        self.assertIsNone(fields['year'])
        self.assertIsNone(fields['month'])
        self.assertIsNone(fields['day'])

    def test_removes_time_redundancy(self):
        """Test removes hour/minute/seconds when time field present."""
        input_fields = ['time', 'hour', 'minute', 'seconds', 'latitude']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        self.assertEqual(fields['time'], 'time')
        self.assertIsNone(fields['hour'])
        self.assertIsNone(fields['minute'])
        self.assertIsNone(fields['seconds'])

    def test_handles_duplicates_by_score(self):
        """Test handles duplicate field matches by keeping highest score."""
        # Create a scenario where a field could match multiple names
        input_fields = ['mag', 'magnitude', 'latitude', 'time']
        with patch('builtins.print'):
            fields = _guess_field_names(input_fields)
        # Both 'mag' and 'magnitude' match perfectly,
        # but the function picks the first perfect match
        self.assertIn(fields['mag'], ['mag', 'magnitude'])


class TestCSVFileInfo(unittest.TestCase):
    """Test _csv_file_info function."""

    def _create_csv_file(self, lines):
        """Create a temporary CSV file with given lines.

        :param lines: list of strings to write to file
        :type lines: list
        :return: filename
        :rtype: str
        """
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            for line in lines:
                f.write(line + '\n')
            filename = f.name
        return filename

    def test_detects_comma_delimiter(self):
        """Test detection of comma delimiter."""
        filename = self._create_csv_file([
            'lat,lon,depth,mag',
            '10.0,20.0,5.0,3.5',
            '11.0,21.0,6.0,3.7'
        ])
        try:
            delimiter, nrows = _csv_file_info(filename)
            self.assertEqual(delimiter, ',')
            self.assertEqual(nrows, 3)
        finally:
            os.unlink(filename)

    def test_detects_semicolon_delimiter(self):
        """Test detection of semicolon delimiter."""
        filename = self._create_csv_file([
            'lat;lon;depth;mag',
            '10.0;20.0;5.0;3.5',
            '11.0;21.0;6.0;3.7'
        ])
        try:
            delimiter, nrows = _csv_file_info(filename)
            self.assertEqual(delimiter, ';')
            self.assertEqual(nrows, 3)
        finally:
            os.unlink(filename)

    def test_detects_space_delimiter(self):
        """Test detection of space delimiter."""
        filename = self._create_csv_file([
            'lat lon depth mag',
            '10.0 20.0 5.0 3.5',
            '11.0 21.0 6.0 3.7'
        ])
        try:
            delimiter, nrows = _csv_file_info(filename)
            self.assertEqual(delimiter, ' ')
            self.assertEqual(nrows, 3)
        finally:
            os.unlink(filename)


class TestReadOrigTimeFromYMDHMS(unittest.TestCase):
    """Test _read_orig_time_from_ymdhms function."""

    def _test_ymdhms_parsing(
        self,
        year, month, day, hour, minute, seconds,
        expected_year, expected_month, expected_day,
        expected_hour, expected_minute, expected_seconds
    ):
        """Helper to test year/month/day/hour/minute/seconds parsing.

        :param year: year string value
        :param month: month string value
        :param day: day string value
        :param hour: hour string value
        :param minute: minute string value
        :param seconds: seconds string value
        :param expected_year: expected year integer
        :param expected_month: expected month integer
        :param expected_day: expected day integer
        :param expected_hour: expected hour integer
        :param expected_minute: expected minute integer
        :param expected_seconds: expected seconds float
        """
        fields = {
            'year': 'year',
            'month': 'month',
            'day': 'day',
            'hour': 'hour',
            'minute': 'minute',
            'seconds': 'seconds'
        }
        row = {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'seconds': seconds
        }
        result = _read_orig_time_from_ymdhms(row, fields)
        expected = UTCDateTime(
            expected_year, expected_month, expected_day,
            expected_hour, expected_minute, expected_seconds
        )
        self.assertEqual(result, expected)

    def test_reads_complete_datetime(self):
        """Test reading complete date-time from components."""
        self._test_ymdhms_parsing(
            '2023', '5', '15', '14', '30', '45.5',
            2023, 5, 15, 14, 30, 45.5
        )

    def test_handles_two_digit_year(self):
        """Test handles two-digit year (assumes 21st century)."""
        self._test_ymdhms_parsing(
            '23', '5', '15', '14', '30', '0',
            2023, 5, 15, 14, 30, 0
        )

    def test_handles_fractional_seconds(self):
        """Test handles fractional seconds."""
        self._test_ymdhms_parsing(
            '2023', '5', '15', '14', '30', '45.123',
            2023, 5, 15, 14, 30, 45.123
        )


class TestSplitDateTime(unittest.TestCase):
    """Test _split_date_time function."""

    def _assert_split_date_time(self, input_str, expected_date, expected_time):
        """Helper to test date/time splitting.

        :param input_str: input datetime string
        :param expected_date: expected date part
        :param expected_time: expected time part
        """
        date, time = _split_date_time(input_str)
        self.assertEqual(date, expected_date)
        self.assertEqual(time, expected_time)

    def test_splits_iso8601_format(self):
        """Test splitting ISO8601 format with 'T'."""
        self._assert_split_date_time(
            '2023-05-15T14:30:45', '2023-05-15', '14:30:45')

    def test_splits_space_separated_with_date_first(self):
        """Test splitting space-separated date time."""
        self._assert_split_date_time(
            '2023-05-15 14:30:45', '2023-05-15', '14:30:45')

    def test_splits_space_separated_with_time_first(self):
        """Test splitting when time comes first."""
        self._assert_split_date_time(
            '14:30:45 2023-05-15', '2023-05-15', '14:30:45')

    def test_handles_no_separator(self):
        """Test handles string with no separator."""
        self._assert_split_date_time(
            '2023-05-15', '2023-05-15', '')

    def test_handles_ambiguous_format(self):
        """Test handles ambiguous format."""
        date, _time = _split_date_time('2023 05')
        # Should return as date since it can't be split properly
        self.assertIn('2023', date)


class TestNormalizeDateFormat(unittest.TestCase):
    """Test _normalize_date_format function."""

    def test_normalizes_day_month_year_with_dash(self):
        """Test normalizes day-month-year format with dash."""
        result = _normalize_date_format('15-05-2023')
        self.assertEqual(result, '2023-05-15')

    def test_normalizes_day_month_year_with_slash(self):
        """Test normalizes day-month-year format with slash."""
        result = _normalize_date_format('15/05/2023')
        self.assertEqual(result, '2023/05/15')

    def test_keeps_year_month_day_unchanged(self):
        """Test keeps year-month-day format unchanged."""
        result = _normalize_date_format('2023-05-15')
        # This stays unchanged because it doesn't match the d-m-y pattern
        self.assertEqual(result, '2023-05-15')

    def test_handles_empty_string(self):
        """Test handles empty string."""
        result = _normalize_date_format('')
        self.assertEqual(result, '')

    def test_handles_invalid_format(self):
        """Test handles invalid date format."""
        result = _normalize_date_format('invalid-date-format')
        self.assertEqual(result, 'invalid-date-format')

    def test_validates_month_range(self):
        """Test validates month is 1-12."""
        result = _normalize_date_format('32-05-2023')
        # Should not normalize because day > 31
        # Actually, 32 <= 31 is false, but let's check the logic
        self.assertEqual(result, '32-05-2023')

    def test_validates_year_range(self):
        """Test validates year is in reasonable range."""
        result = _normalize_date_format('15-05-3023')
        # Year 3023 is out of range (1800-2100)
        self.assertEqual(result, '15-05-3023')


class TestReadOrigTimeFromDatetime(unittest.TestCase):
    """Test _read_orig_time_from_datetime function."""

    def _test_datetime_parsing(self, fields, row, expected_datetime_str):
        """Helper to test datetime parsing.

        :param fields: fields dictionary with date/time field names
        :param row: row dictionary with date/time values
        :param expected_datetime_str: expected datetime string for UTCDateTime
        """
        result = _read_orig_time_from_datetime(row, fields)
        expected = UTCDateTime(expected_datetime_str)
        self.assertEqual(result, expected)

    def test_reads_iso8601_datetime(self):
        """Test reading ISO8601 datetime."""
        self._test_datetime_parsing(
            {'date': 'date', 'time': 'time'},
            {'date': '2023-05-15', 'time': '14:30:45'},
            '2023-05-15T14:30:45'
        )

    def test_reads_combined_datetime_from_date_field(self):
        """Test reading datetime when combined in date field."""
        self._test_datetime_parsing(
            {'date': 'datetime', 'time': None},
            {'datetime': '2023-05-15T14:30:45'},
            '2023-05-15T14:30:45'
        )

    def test_reads_combined_datetime_from_time_field(self):
        """Test reading datetime when combined in time field."""
        self._test_datetime_parsing(
            {'date': None, 'time': 'datetime'},
            {'datetime': '2023-05-15 14:30:45'},
            '2023-05-15T14:30:45'
        )

    def test_normalizes_european_date_format(self):
        """Test normalizes European date format."""
        self._test_datetime_parsing(
            {'date': 'date', 'time': 'time'},
            {'date': '15-05-2023', 'time': '14:30:45'},
            '2023-05-15T14:30:45'
        )

    def test_handles_alternative_format(self):
        """Test handles alternative YYYYMMDD.hhmmss format."""
        self._test_datetime_parsing(
            {'date': 'datetime', 'time': None},
            {'datetime': '20230515.143045'},
            '20230515 143045'
        )

    def test_raises_error_for_invalid_datetime(self):
        """Test raises ValueError for invalid datetime."""
        fields = {'date': 'date', 'time': 'time'}
        row = {'date': 'invalid', 'time': 'invalid'}
        with self.assertRaises((ValueError, TypeError)):
            _read_orig_time_from_datetime(row, fields)

    def test_raises_error_for_empty_datetime(self):
        """Test raises ValueError for empty datetime."""
        fields = {'date': None, 'time': None}
        row = {}
        with self.assertRaises(ValueError):
            _read_orig_time_from_datetime(row, fields)


class TestReadOrigTimeFromRow(unittest.TestCase):
    """Test _read_orig_time_from_row function."""

    def test_uses_ymdhms_when_time_field_none(self):
        """Test uses YMDHMS components when time field is None."""
        fields = {
            'time': None,
            'year': 'year',
            'month': 'month',
            'day': 'day',
            'hour': 'hour',
            'minute': 'minute',
            'seconds': 'seconds'
        }
        row = {
            'year': '2023',
            'month': '5',
            'day': '15',
            'hour': '14',
            'minute': '30',
            'seconds': '45'
        }
        result = _read_orig_time_from_row(row, fields)
        expected = UTCDateTime(2023, 5, 15, 14, 30, 45)
        self.assertEqual(result, expected)

    def test_uses_datetime_when_time_field_present(self):
        """Test uses datetime field when present."""
        fields = {'time': 'time', 'date': 'date'}
        row = {'date': '2023-05-15', 'time': '14:30:45'}
        result = _read_orig_time_from_row(row, fields)
        expected = UTCDateTime('2023-05-15T14:30:45')
        self.assertEqual(result, expected)


class TestReadCSVRow(unittest.TestCase):
    """Test _read_csv_row function."""

    def test_reads_complete_row(self):
        """Test reading a complete CSV row."""
        fields = {
            None: None,
            'evid': None,
            'date': 'date',
            'time': 'time',
            'lat': 'latitude',
            'lon': 'longitude',
            'depth': 'depth',
            'mag': 'magnitude',
            'mag_type': 'mag_type',
            'event_type': 'event_type'
        }
        row = {
            'date': '2023-05-15',
            'time': '14:30:45',
            'latitude': '42.5',
            'longitude': '13.2',
            'depth': '10.0',
            'magnitude': '3.5',
            'mag_type': 'ML',
            'event_type': 'earthquake'
        }
        with patch('builtins.print'):
            ev = _read_csv_row(row, fields, 'km', 'ML')

        self.assertIsInstance(ev, Event)
        self.assertEqual(ev.origins[0].latitude, 42.5)
        self.assertEqual(ev.origins[0].longitude, 13.2)
        self.assertEqual(ev.origins[0].depth, 10000.0)  # converted to meters
        self.assertEqual(ev.magnitudes[0].mag, 3.5)
        self.assertEqual(ev.magnitudes[0].magnitude_type, 'ML')

    def test_generates_evid_when_missing(self):
        """Test generates event ID when missing."""
        fields = {
            None: None,
            'evid': None,
            'date': 'date',
            'time': 'time',
            'lat': 'latitude',
            'lon': 'longitude',
            'depth': 'depth',
            'mag': 'magnitude',
            'mag_type': None,
            'event_type': 'event_type'
        }
        row = {
            'date': '2023-05-15',
            'time': '14:30:45',
            'latitude': '42.5',
            'longitude': '13.2',
            'depth': '10.0',
            'magnitude': '3.5',
            'event_type': 'None'
        }
        with patch('builtins.print'):
            ev = _read_csv_row(row, fields, 'km', 'ML')

        self.assertIsInstance(ev, Event)
        self.assertTrue(ev.resource_id.id.startswith('scat'))

    def test_handles_depth_in_meters(self):
        """Test handles depth already in meters."""
        fields = {
            None: None,
            'evid': None,
            'date': 'date',
            'time': 'time',
            'lat': 'latitude',
            'lon': 'longitude',
            'depth': 'depth',
            'mag': 'magnitude',
            'mag_type': None,
            'event_type': 'event_type'
        }
        row = {
            'date': '2023-05-15',
            'time': '14:30:45',
            'latitude': '42.5',
            'longitude': '13.2',
            'depth': '10000.0',
            'magnitude': '3.5',
            'event_type': 'None'
        }
        with patch('builtins.print'):
            ev = _read_csv_row(row, fields, 'm', 'ML')

        self.assertEqual(ev.origins[0].depth, 10000.0)  # stays in meters

    def test_uses_default_mag_type(self):
        """Test uses default magnitude type when none specified."""
        fields = {
            None: None,
            'evid': None,
            'date': 'date',
            'time': 'time',
            'lat': 'latitude',
            'lon': 'longitude',
            'depth': 'depth',
            'mag': 'magnitude',
            'mag_type': None,
            'event_type': 'event_type'
        }
        row = {
            'date': '2023-05-15',
            'time': '14:30:45',
            'latitude': '42.5',
            'longitude': '13.2',
            'depth': '10.0',
            'magnitude': '3.5',
            'event_type': 'None'
        }
        with patch('builtins.print'):
            ev = _read_csv_row(row, fields, 'km', 'MW')

        self.assertEqual(ev.magnitudes[0].magnitude_type, 'MW')

    def test_handles_none_values(self):
        """Test handles None values gracefully."""
        fields = {
            None: None,
            'evid': None,
            'date': 'date',
            'time': 'time',
            'lat': 'latitude',
            'lon': 'longitude',
            'depth': 'depth',
            'mag': 'magnitude',
            'mag_type': None,
            'event_type': 'event_type'
        }
        row = {
            'date': '2023-05-15',
            'time': '14:30:45',
            'latitude': '',
            'longitude': '',
            'depth': '',
            'magnitude': '',
            'event_type': 'None'
        }
        with patch('builtins.print'):
            ev = _read_csv_row(row, fields, 'm', 'ML')

        self.assertIsNone(ev.origins[0].latitude)
        self.assertIsNone(ev.origins[0].longitude)
        self.assertIsNone(ev.origins[0].depth)
        self.assertIsNone(ev.magnitudes[0].mag)


class TestReadCSV(unittest.TestCase):
    """Test _read_csv function."""

    def test_reads_csv_with_header(self):
        """Test reading CSV with header row."""
        csv_content = """latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        fp = StringIO(csv_content)
        with patch('builtins.print'):
            cat = _read_csv(fp, ',', None, 3, 'km')

        self.assertIsInstance(cat, Catalog)
        self.assertEqual(len(cat), 2)
        self.assertEqual(cat[0].origins[0].latitude, 42.5)
        self.assertEqual(cat[1].origins[0].latitude, 43.0)

    def test_reads_csv_without_header(self):
        """Test reading CSV without header row."""
        csv_content = """42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        fp = StringIO(csv_content)
        column_names = ['latitude', 'longitude', 'depth', 'magnitude',
                        'origin_time']
        with patch('builtins.print'):
            cat = _read_csv(fp, ',', column_names, 2, 'km')

        self.assertIsInstance(cat, Catalog)
        self.assertEqual(len(cat), 2)

    def test_handles_space_delimiter(self):
        """Test handles space delimiter with multiple spaces."""
        csv_content = """latitude  longitude  depth  magnitude  origin_time
42.5  13.2  10.0  3.5  2023-05-15T14:30:45
43.0  14.0  15.0  4.0  2023-05-16T10:00:00
"""
        fp = StringIO(csv_content)
        with patch('builtins.print'):
            cat = _read_csv(fp, ' ', None, 3, 'km')

        self.assertIsInstance(cat, Catalog)
        self.assertEqual(len(cat), 2)

    def test_skips_invalid_rows(self):
        """Test skips rows with invalid data."""
        csv_content = """latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
invalid,invalid,invalid,invalid,invalid
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        fp = StringIO(csv_content)
        with patch('builtins.print'):
            cat = _read_csv(fp, ',', None, 4, 'km')

        # Should skip the invalid row
        self.assertEqual(len(cat), 2)

    def test_guesses_mag_type_from_field_name(self):
        """Test guesses magnitude type from field name."""
        csv_content = """latitude,longitude,depth,ml,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
"""
        fp = StringIO(csv_content)
        with patch('builtins.print'):
            cat = _read_csv(fp, ',', None, 2, 'km')

        self.assertEqual(cat[0].magnitudes[0].magnitude_type, 'ml')


class TestReadCatalogFromCSV(unittest.TestCase):
    """Test read_catalog_from_csv function."""

    def test_reads_catalog_from_csv_file(self):
        """Test reading catalog from CSV file."""
        csv_content = """latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(filename, depth_units='km')

            with patch('builtins.print'):
                cat = read_catalog_from_csv(config)

            self.assertIsInstance(cat, Catalog)
            self.assertEqual(len(cat), 2)
        finally:
            os.unlink(filename)

    def test_raises_error_for_invalid_depth_units(self):
        """Test raises error for invalid depth units."""
        csv_content = """lat,lon,depth,mag,time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(filename, depth_units='invalid')

            with self.assertRaises(ValueError):
                read_catalog_from_csv(config)
        finally:
            os.unlink(filename)

    def test_auto_detects_depth_units(self):
        """Test auto-detects depth units when not specified."""
        csv_content = """latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(filename, depth_units=None)

            with patch('builtins.print'):
                cat = read_catalog_from_csv(config)

            # Depths should be converted to meters (10.0 km -> 10000 m)
            self.assertEqual(cat[0].origins[0].depth, 10000.0)
        finally:
            os.unlink(filename)

    def test_handles_large_depth_as_meters(self):
        """Test treats large depth values as meters."""
        csv_content = """latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10000.0,3.5,2023-05-15T14:30:45
43.0,14.0,15000.0,4.0,2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(filename, depth_units=None)

            with patch('builtins.print'):
                cat = read_catalog_from_csv(config)

            # Depth should stay as is (already in meters)
            self.assertEqual(cat[0].origins[0].depth, 10000.0)
        finally:
            os.unlink(filename)

    def test_uses_custom_delimiter(self):
        """Test uses custom delimiter when specified."""
        csv_content = """latitude;longitude;depth;magnitude;origin_time
42.5;13.2;10.0;3.5;2023-05-15T14:30:45
43.0;14.0;15.0;4.0;2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(
                filename, depth_units='km', delimiter=';'
            )

            with patch('builtins.print'):
                cat = read_catalog_from_csv(config)

            self.assertEqual(len(cat), 2)
        finally:
            os.unlink(filename)

    def test_uses_custom_column_names(self):
        """Test uses custom column names when specified."""
        csv_content = """42.5,13.2,10.0,3.5,2023-05-15T14:30:45
43.0,14.0,15.0,4.0,2023-05-16T10:00:00
"""
        with tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv'
        ) as f:
            f.write(csv_content)
            filename = f.name

        try:
            config = create_mock_config(
                filename,
                depth_units='km',
                delimiter=',',
                column_names=[
                    'latitude', 'longitude', 'depth',
                    'magnitude', 'origin_time'
                ]
            )

            with patch('builtins.print'):
                cat = read_catalog_from_csv(config)

            self.assertEqual(len(cat), 2)
            self.assertEqual(cat[0].origins[0].latitude, 42.5)
        finally:
            os.unlink(filename)


if __name__ == '__main__':
    unittest.main()

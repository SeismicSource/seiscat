# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Unit tests for the JMA hypocenter format reader module.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from obspy import UTCDateTime
from obspy.core.event import Catalog
from seiscat.sources.jma import (
    JMA_RECORD_LENGTH,
    _parse_fixed_decimal,
    _parse_degrees,
    _parse_angle,
    _parse_depth,
    _parse_magnitude,
    _parse_magnitude_type,
    _read_jma_record,
    _looks_like_jma_record,
    is_jma_hypocenter_file,
    read_catalog_from_jma,
)


def _record(*parts):
    """Join the parts of a JMA record and pad it to 96 characters."""
    record = ''.join(parts)
    assert len(record) <= JMA_RECORD_LENGTH
    return record.ljust(JMA_RECORD_LENGTH)


# JMA record, depth-free method, positive coordinates,
# magnitude type "v" (MV from 2 or 3 stations)
# columns 1-17: record type, origin time (JST)
# columns 18-21: standard error on origin time
# columns 22-28: latitude (degrees + minutes)
# columns 29-32: standard error on latitude
# columns 33-40: longitude (degrees + minutes)
# columns 41-44: standard error on longitude
# columns 45-49: depth (km, 2 implied decimals)
# columns 50-52: standard error on depth
# columns 53-55: magnitude and magnitude type
# columns 56-58: second magnitude and magnitude type
# columns 59-61: travel time table, precision, subsidiary information
# columns 62-64: max intensity, damage class, tsunami class
# columns 65-68: district number, region number
# columns 69-92: region name
# columns 93-96: number of stations, determination flag
JMA_RECORD_DEPTH_FREE = _record(
    'J', '2024', '01', '01', '00', '00', '0458',
    ' 008',
    ' 32', '3863',
    ' 020',
    ' 131', '5911',
    ' 042',
    ' 3621',
    '077',
    '04', 'v',
    '   ',
    '7', '1', '1',
    '   ',
    '7', '300',
    'HYUGANADA REGION'.ljust(24),
    ' 17', 'A',
)

# JMA record, depth-slice method (depth is an integer in columns 45-47)
# and no magnitude
JMA_RECORD_DEPTH_SLICE = _record(
    'J', '2024', '01', '01', '00', '31', '4180',
    ' 085',
    ' 43', '5430',
    ' 453',
    ' 149', '1379',
    ' 388',
    ' 30  ',
    '   ',
    '  ', ' ',
    '   ',
    '7', '3', '1',
    '   ',
    '1', ' 25',
    'SE OFF ETOROFU'.ljust(24),
    ' 12', 'S',
)

# JMA record with a magnitude below -0.9 (coded as "A0" = -1.0)
JMA_RECORD_NEGATIVE_MAG = _record(
    'J', '2024', '01', '05', '03', '43', '2235',
    '    ',
    ' 33', '3025',
    '    ',
    ' 132', '4185',
    '    ',
    ' 3066',
    '   ',
    'A0', 'v',
    '   ',
    '5', 'M', '5',
    '   ',
    '6', '235',
    'SW EHIME PREF'.ljust(24),
    '  8', 'a',
)

# USGS record (record type "U"), with negative latitude and longitude,
# depth-slice method, and magnitude type "B" (mb)
JMA_RECORD_USGS = _record(
    'U', '2024', '01', '19', '07', '12', '2176',
    '    ',
    '-18', '5462',
    '    ',
    '-175', '2535',
    '    ',
    '209  ',
    '   ',
    '61', 'B',
    '         ',
    '9',
    '   ',
    'TONGA'.ljust(24),
    '   ', ' ',
)

# USGS record with a single-digit negative latitude: the sign is separated
# from the digit by a blank ("- 5" = -5 degrees)
JMA_RECORD_USGS_BLANK_SIGN = _record(
    'U', '2024', '03', '22', '17', '52', '5900',
    '    ',
    '- 5', '5252',
    '    ',
    ' 112', '2188',
    '    ',
    ' 10  ',
    '   ',
    '60', 'B',
    '64', 'S',
    '    3 9   ',
    'JAVA SEA'.ljust(24),
    '   ', ' ',
)

CSV_CONTENT = """\
latitude,longitude,depth,magnitude,origin_time
42.5,13.2,10.0,3.5,2023-05-15T14:30:45
"""


def create_mock_config(filename, depth_units=None):
    """Create a mock config object for testing."""
    args = MagicMock()
    args.fromfile = [filename]
    args.depth_units = depth_units
    args.action = 'initdb'
    return {'args': args}


def _write_tmp_file(content):
    """Write content to a temporary file and return its name."""
    with tempfile.NamedTemporaryFile(
        mode='w', delete=False, suffix='.jma'
    ) as f:
        f.write(content)
        return f.name


class TestParseFixedDecimal(unittest.TestCase):
    """Test _parse_fixed_decimal function."""

    def test_two_decimals(self):
        """Test a field with 2 implied decimals."""
        self.assertAlmostEqual(_parse_fixed_decimal('0458', 2), 4.58)

    def test_leading_spaces(self):
        """Test a field with leading spaces."""
        self.assertAlmostEqual(_parse_fixed_decimal('  008', 2), 0.08)

    def test_blank_decimal_part(self):
        """Test a field with a blank decimal part."""
        self.assertAlmostEqual(_parse_fixed_decimal('04  ', 2), 4.0)

    def test_blank_field(self):
        """Test a blank field returns None."""
        self.assertIsNone(_parse_fixed_decimal('    ', 2))


class TestParseDegrees(unittest.TestCase):
    """Test _parse_degrees function."""

    def test_positive(self):
        """Test a positive degrees field."""
        self.assertEqual(_parse_degrees(' 32'), 32)

    def test_negative(self):
        """Test a negative degrees field."""
        self.assertEqual(_parse_degrees('-175'), -175)

    def test_blank_after_sign(self):
        """Test a negative degrees field with a blank after the sign."""
        self.assertEqual(_parse_degrees('- 5'), -5)
        self.assertEqual(_parse_degrees('- 0'), 0)

    def test_blank_field(self):
        """Test a blank degrees field returns None."""
        self.assertIsNone(_parse_degrees('   '))


class TestParseAngle(unittest.TestCase):
    """Test _parse_angle function."""

    def test_positive(self):
        """Test a positive angle."""
        self.assertAlmostEqual(_parse_angle(' 32', '3863'), 32 + 38.63 / 60)

    def test_negative(self):
        """Test a negative angle."""
        self.assertAlmostEqual(
            _parse_angle('-175', '2535'), -(175 + 25.35 / 60))

    def test_blank_after_sign(self):
        """Test a negative angle with a blank after the sign."""
        self.assertAlmostEqual(_parse_angle('- 5', '5252'), -(5 + 52.52 / 60))

    def test_zero_degrees_with_negative_sign(self):
        """Test a zero degrees value with a negative sign."""
        self.assertAlmostEqual(_parse_angle('- 0', '0281'), -(2.81 / 60))

    def test_blank_minutes(self):
        """Test blank minutes are read as zero."""
        self.assertAlmostEqual(_parse_angle(' 32', '    '), 32.0)

    def test_blank_degrees(self):
        """Test blank degrees return None."""
        self.assertIsNone(_parse_angle('   ', '3863'))


class TestParseDepth(unittest.TestCase):
    """Test _parse_depth function."""

    def test_depth_free_method(self):
        """Test a depth with 2 implied decimals."""
        self.assertAlmostEqual(_parse_depth(' 3621'), 36.21)

    def test_depth_slice_method(self):
        """Test an integer depth."""
        self.assertAlmostEqual(_parse_depth(' 30  '), 30.0)

    def test_three_digit_depth_slice(self):
        """Test a three-digit integer depth."""
        self.assertAlmostEqual(_parse_depth('204  '), 204.0)

    def test_blank_depth(self):
        """Test a blank depth returns None."""
        self.assertIsNone(_parse_depth('     '))


class TestParseMagnitude(unittest.TestCase):
    """Test _parse_magnitude function."""

    def test_positive(self):
        """Test a positive magnitude."""
        self.assertAlmostEqual(_parse_magnitude('45'), 4.5)

    def test_negative(self):
        """Test a negative magnitude."""
        self.assertAlmostEqual(_parse_magnitude('-9'), -0.9)

    def test_letter_codes(self):
        """Test magnitude letter codes."""
        self.assertAlmostEqual(_parse_magnitude('A0'), -1.0)
        self.assertAlmostEqual(_parse_magnitude('A3'), -1.3)
        self.assertAlmostEqual(_parse_magnitude('B0'), -2.0)
        self.assertAlmostEqual(_parse_magnitude('C0'), -3.0)

    def test_blank(self):
        """Test a blank magnitude returns None."""
        self.assertIsNone(_parse_magnitude('  '))


class TestParseMagnitudeType(unittest.TestCase):
    """Test _parse_magnitude_type function."""

    def test_known_types(self):
        """Test known magnitude types."""
        self.assertEqual(_parse_magnitude_type('J'), 'mjma')
        self.assertEqual(_parse_magnitude_type('D'), 'md')
        self.assertEqual(_parse_magnitude_type('d'), 'md')
        self.assertEqual(_parse_magnitude_type('V'), 'mv')
        self.assertEqual(_parse_magnitude_type('v'), 'mv')
        self.assertEqual(_parse_magnitude_type('W'), 'mw')
        self.assertEqual(_parse_magnitude_type('B'), 'mb')
        self.assertEqual(_parse_magnitude_type('S'), 'ms')

    def test_unknown_type(self):
        """Test an unknown magnitude type returns None."""
        self.assertIsNone(_parse_magnitude_type(' '))


class TestReadJMARecord(unittest.TestCase):
    """Test _read_jma_record function."""

    def test_depth_free_record(self):
        """Test a record with a depth-free depth."""
        ev = _read_jma_record(JMA_RECORD_DEPTH_FREE)
        orig = ev.origins[0]
        # origin time is in JST and must be converted to UTC
        self.assertEqual(orig.time, UTCDateTime('2023-12-31T15:00:04.58'))
        self.assertAlmostEqual(orig.latitude, 32 + 38.63 / 60)
        self.assertAlmostEqual(orig.longitude, 131 + 59.11 / 60)
        # depths are converted to meters
        self.assertAlmostEqual(orig.depth, 36210.0)
        self.assertAlmostEqual(orig.quality.standard_error, 0.08)
        self.assertEqual(orig.quality.associated_station_count, 17)
        mag = ev.magnitudes[0]
        self.assertAlmostEqual(mag.mag, 0.4)
        self.assertEqual(mag.magnitude_type, 'mv')
        self.assertEqual(ev.event_type, 'earthquake')
        self.assertEqual(ev.creation_info.agency_id, 'JMA')
        self.assertEqual(ev.extra['jma_region']['value'], 'HYUGANADA REGION')
        self.assertEqual(ev.extra['jma_region_number']['value'], 300)
        self.assertEqual(ev.extra['jma_district_number']['value'], 7)
        self.assertEqual(ev.extra['jma_station_count']['value'], 17)
        self.assertEqual(ev.extra['jma_determination_flag']['value'], 'A')
        self.assertEqual(ev.extra['jma_precision']['value'], '1')
        self.assertEqual(ev.extra['jma_travel_time_table']['value'], '7')

    def test_depth_slice_record(self):
        """Test a record with a depth-slice depth and no magnitude."""
        ev = _read_jma_record(JMA_RECORD_DEPTH_SLICE)
        orig = ev.origins[0]
        self.assertEqual(orig.time, UTCDateTime('2023-12-31T15:31:41.80'))
        self.assertAlmostEqual(orig.depth, 30000.0)
        self.assertIsNone(ev.magnitudes[0].mag)
        self.assertIsNone(ev.magnitudes[0].magnitude_type)
        self.assertEqual(ev.extra['jma_region']['value'], 'SE OFF ETOROFU')
        self.assertEqual(ev.extra['jma_determination_flag']['value'], 'S')

    def test_negative_magnitude_record(self):
        """Test a record with a negative magnitude code."""
        ev = _read_jma_record(JMA_RECORD_NEGATIVE_MAG)
        self.assertAlmostEqual(ev.magnitudes[0].mag, -1.0)
        self.assertEqual(ev.magnitudes[0].magnitude_type, 'mv')
        self.assertEqual(ev.extra['jma_precision']['value'], 'M')
        # subsidiary information 5: low-frequency earthquake
        self.assertEqual(ev.event_type, 'earthquake')

    def test_usgs_record(self):
        """Test a USGS record with negative coordinates."""
        ev = _read_jma_record(JMA_RECORD_USGS)
        orig = ev.origins[0]
        self.assertEqual(orig.time, UTCDateTime('2024-01-18T22:12:21.76'))
        self.assertAlmostEqual(orig.latitude, -(18 + 54.62 / 60))
        self.assertAlmostEqual(orig.longitude, -(175 + 25.35 / 60))
        self.assertAlmostEqual(orig.depth, 209000.0)
        self.assertAlmostEqual(ev.magnitudes[0].mag, 6.1)
        self.assertEqual(ev.magnitudes[0].magnitude_type, 'mb')
        self.assertIsNone(ev.event_type)
        self.assertEqual(ev.creation_info.agency_id, 'USGS')

    def test_usgs_record_with_blank_after_sign(self):
        """Test a USGS record with single-digit negative latitude."""
        ev = _read_jma_record(JMA_RECORD_USGS_BLANK_SIGN)
        orig = ev.origins[0]
        self.assertAlmostEqual(orig.latitude, -(5 + 52.52 / 60))
        self.assertAlmostEqual(orig.longitude, 112 + 21.88 / 60)
        self.assertAlmostEqual(orig.depth, 10000.0)
        self.assertAlmostEqual(ev.magnitudes[0].mag, 6.0)
        self.assertEqual(ev.magnitudes[0].magnitude_type, 'mb')

    def test_record_without_magnitude(self):
        """Test that a blank magnitude is read as None."""
        record = (
            f'{JMA_RECORD_DEPTH_FREE[:52]}    '
            f'{JMA_RECORD_DEPTH_FREE[56:]}'
        )
        ev = _read_jma_record(record)
        self.assertIsNone(ev.magnitudes[0].mag)

    def test_invalid_record(self):
        """Test that an invalid record raises ValueError."""
        with self.assertRaises(ValueError):
            _read_jma_record('not a JMA record')


class TestLooksLikeJMARecord(unittest.TestCase):
    """Test _looks_like_jma_record function."""

    def test_valid_records(self):
        """Test valid records are recognized."""
        self.assertTrue(_looks_like_jma_record(JMA_RECORD_DEPTH_FREE))
        self.assertTrue(_looks_like_jma_record(JMA_RECORD_USGS))
        self.assertTrue(_looks_like_jma_record(JMA_RECORD_USGS_BLANK_SIGN))

    def test_invalid_records(self):
        """Test invalid records are not recognized."""
        self.assertFalse(_looks_like_jma_record(''))
        self.assertFalse(_looks_like_jma_record('latitude,longitude'))
        self.assertFalse(_looks_like_jma_record('J2024'))


class TestIsJMAHypocenterFile(unittest.TestCase):
    """Test is_jma_hypocenter_file function."""

    def test_jma_file(self):
        """Test a JMA file is recognized."""
        filename = _write_tmp_file(
            f'{JMA_RECORD_DEPTH_FREE}\n{JMA_RECORD_USGS}\n')
        try:
            self.assertTrue(is_jma_hypocenter_file(filename))
        finally:
            os.unlink(filename)

    def test_csv_file(self):
        """Test a CSV file is not recognized as a JMA file."""
        filename = _write_tmp_file(CSV_CONTENT)
        try:
            self.assertFalse(is_jma_hypocenter_file(filename))
        finally:
            os.unlink(filename)

    def test_missing_file(self):
        """Test a missing file is not recognized as a JMA file."""
        self.assertFalse(is_jma_hypocenter_file('/nonexistent/h2024'))

    def test_empty_file(self):
        """Test an empty file is not recognized as a JMA file."""
        filename = _write_tmp_file('')
        try:
            self.assertFalse(is_jma_hypocenter_file(filename))
        finally:
            os.unlink(filename)


class TestReadCatalogFromJMA(unittest.TestCase):
    """Test read_catalog_from_jma function."""

    def test_reads_catalog_from_jma_file(self):
        """Test reading a catalog from a JMA file."""
        filename = _write_tmp_file(
            f'{JMA_RECORD_DEPTH_FREE}\n'
            f'{JMA_RECORD_DEPTH_SLICE}\n'
            f'{JMA_RECORD_USGS}\n'
        )
        try:
            config = create_mock_config(filename)
            with patch('builtins.print'):
                cat = read_catalog_from_jma(config)
            self.assertIsInstance(cat, Catalog)
            self.assertEqual(len(cat), 3)
        finally:
            os.unlink(filename)

    def test_unique_evids_for_same_origin_time(self):
        """Test events sharing the origin time get unique evids."""
        filename = _write_tmp_file(
            f'{JMA_RECORD_DEPTH_FREE}\n{JMA_RECORD_DEPTH_FREE}\n')
        try:
            config = create_mock_config(filename)
            with patch('builtins.print'):
                cat = read_catalog_from_jma(config)
            evids = [str(ev.resource_id.id) for ev in cat]
            self.assertEqual(len(set(evids)), 2)
        finally:
            os.unlink(filename)

    def test_raises_error_for_non_jma_file(self):
        """Test an error is raised for a non-JMA file."""
        filename = _write_tmp_file(CSV_CONTENT)
        try:
            config = create_mock_config(filename)
            with patch('builtins.print'):
                with self.assertRaises(ValueError):
                    read_catalog_from_jma(config)
        finally:
            os.unlink(filename)

    def test_raises_error_for_missing_file(self):
        """Test an error is raised for a missing file."""
        config = create_mock_config('/nonexistent/h2024')
        with self.assertRaises(FileNotFoundError):
            read_catalog_from_jma(config)

    def test_depth_units_are_ignored(self):
        """Test that --depth_units is ignored for JMA files."""
        filename = _write_tmp_file(f'{JMA_RECORD_DEPTH_FREE}\n')
        try:
            config = create_mock_config(filename, depth_units='m')
            with patch('builtins.print'):
                cat = read_catalog_from_jma(config)
            self.assertAlmostEqual(cat[0].origins[0].depth, 36210.0)
        finally:
            os.unlink(filename)


if __name__ == '__main__':
    unittest.main()

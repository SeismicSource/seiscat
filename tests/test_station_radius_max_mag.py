# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Test the station_radius_max_mag configuration parameter.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import unittest
from seiscat.fetchdata.mass_downloader import _calculate_station_radius_max


class TestStationRadiusMaxMag(unittest.TestCase):
    """Test magnitude-dependent station radius calculation."""

    def test_magnitude_bins_discrete(self):
        """Test discrete binning behavior."""
        station_radius_max_mag = "2.0: 1.0, 3.0: 2.0, 4.0: 3.0"
        # Test exact bin values
        result = _calculate_station_radius_max(
            2.0, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 1.0)
        result = _calculate_station_radius_max(
            3.0, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 2.0)
        result = _calculate_station_radius_max(
            4.0, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 3.0)
        # Test discrete binning (no interpolation)
        # Magnitude 2.5 should use bin for mag 2.0
        result = _calculate_station_radius_max(
            2.5, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 1.0)
        # Magnitude 3.5 should use bin for mag 3.0
        result = _calculate_station_radius_max(
            3.5, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 2.0)
        # Magnitude 3.9 should use bin for mag 3.0
        result = _calculate_station_radius_max(
            3.9, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 2.0)

    def test_magnitude_bins_boundaries(self):
        """Test binning at boundary values."""
        station_radius_max_mag = "2.0: 1.0, 3.0: 2.0, 4.0: 3.0"
        # Below minimum magnitude: use first bin
        result = _calculate_station_radius_max(
            1.0, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 1.0)
        # At or above maximum magnitude: use last bin
        result = _calculate_station_radius_max(
            5.0, station_radius_max_mag, 0, 10)
        self.assertEqual(result, 3.0)

    def test_magnitude_bins_with_bounds(self):
        """Test bounds are applied correctly for magnitude bins."""
        station_radius_max_mag = "2.0: 1.0, 3.0: 2.0, 4.0: 3.0"
        # Test lower bound
        result = _calculate_station_radius_max(
            2.0, station_radius_max_mag, 1.5, 10)
        self.assertEqual(result, 1.5)  # Should be constrained by min
        # Test upper bound
        result = _calculate_station_radius_max(
            4.0, station_radius_max_mag, 0, 2.5)
        self.assertEqual(result, 2.5)  # Should be constrained by max

    def test_mathematical_expression(self):
        """Test mathematical expression evaluation."""
        station_radius_max_mag = "2.0 * mag - 3.0"
        result = _calculate_station_radius_max(
            2.0, station_radius_max_mag, 0, 10)
        self.assertAlmostEqual(result, 1.0, places=5)
        result = _calculate_station_radius_max(
            3.0, station_radius_max_mag, 0, 10)
        self.assertAlmostEqual(result, 3.0, places=5)
        result = _calculate_station_radius_max(
            4.5, station_radius_max_mag, 0, 10)
        self.assertAlmostEqual(result, 6.0, places=5)

    def test_mathematical_expression_with_bounds(self):
        """Test bounds applied correctly for mathematical expressions."""
        station_radius_max_mag = "2.0 * mag - 3.0"
        # Test lower bound
        result = _calculate_station_radius_max(
            2.0, station_radius_max_mag, 2.0, 10)
        self.assertEqual(result, 2.0)  # Should be constrained by min
        # Test upper bound
        result = _calculate_station_radius_max(
            5.0, station_radius_max_mag, 0, 5.0)
        self.assertEqual(result, 5.0)  # Should be constrained by max

    def test_none_parameter(self):
        """Test that None returns the default station_radius_max."""
        result = _calculate_station_radius_max(3.0, None, 0, 5.0)
        self.assertEqual(result, 5.0)

    def test_invalid_bins_format(self):
        """Test handling of invalid bins format."""
        station_radius_max_mag = "invalid format"
        # Should return default station_radius_max
        result = _calculate_station_radius_max(
            3.0, station_radius_max_mag, 0, 5.0)
        self.assertEqual(result, 5.0)

    def test_invalid_expression(self):
        """Test handling of invalid mathematical expression."""
        station_radius_max_mag = "invalid_var * 2"
        # Should return default station_radius_max
        result = _calculate_station_radius_max(
            3.0, station_radius_max_mag, 0, 5.0)
        self.assertEqual(result, 5.0)

    def test_complex_expression(self):
        """Test more complex mathematical expressions."""
        # Test with pow function
        station_radius_max_mag = "pow(mag, 2) / 2"
        result = _calculate_station_radius_max(
            4.0, station_radius_max_mag, 0, 20)
        self.assertAlmostEqual(result, 8.0, places=5)
        # Test with abs function
        station_radius_max_mag = "abs(mag - 5) + 1"
        result = _calculate_station_radius_max(
            3.0, station_radius_max_mag, 0, 10)
        self.assertAlmostEqual(result, 3.0, places=5)


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Tests for event filtering in plotting dispatchers.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from seiscat.plot.plot_map import plot_catalog_map
from seiscat.plot.plot_timeline import plot_catalog_timeline
from seiscat.plot.plot_utils import (
    filter_events_for_plotting, is_large_n_plotly_mode,
)
from seiscat.plot.plot_timeline_utils import get_event_times_values_and_events


class TestFilterEventsForPlotting(unittest.TestCase):
    """Test shared plotting-event filtering."""

    def test_skips_events_with_missing_coordinates(self):
        """Events missing lat/lon should be skipped with a message."""
        events = [
            {'evid': 'ok', 'lat': 42.0, 'lon': 13.0, 'depth': 10.0},
            {'evid': 'missing-lat', 'lat': None, 'lon': 13.1, 'depth': 8.0},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            filtered = filter_events_for_plotting(
                events,
                backend_name='folium',
            )

        self.assertEqual(filtered, [events[0]])
        self.assertIn(
            'Skipping event "missing-lat" for folium backend: '
            'latitude/longitude are not both defined.',
            output.getvalue(),
        )

    def test_plotly_also_requires_depth(self):
        """Plotly filtering should also reject events without depth."""
        events = [
            {'evid': 'ok', 'lat': 42.0, 'lon': 13.0, 'depth': 10.0},
            {'evid': 'missing-depth', 'lat': 42.1, 'lon': 13.1, 'depth': None},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            filtered = filter_events_for_plotting(
                events,
                backend_name='plotly',
                require_depth=True,
            )

        self.assertEqual(filtered, [events[0]])
        self.assertIn(
            'Skipping event "missing-depth" for plotly backend: '
            'depth is not defined.',
            output.getvalue(),
        )


class TestLargeNPlotlyMode(unittest.TestCase):
    """Test large-N threshold helper for plotly optimizations."""

    def test_threshold_boundary(self):
        """Large-N mode should trigger only above the threshold."""
        self.assertFalse(is_large_n_plotly_mode(10000))
        self.assertTrue(is_large_n_plotly_mode(10001))


class TestPlotDispatchersFiltering(unittest.TestCase):
    """Test map filtering and timeline pass-through behavior."""

    def test_map_dispatcher_passes_only_events_with_coordinates(self):
        """Map backend should receive only events with valid coordinates."""
        backend = MagicMock()
        module = types.ModuleType('seiscat.plot.plot_map_folium')
        module.plot_catalog_map_with_folium = backend
        args = SimpleNamespace(
            backend='folium',
            colorby=None,
            colormap=None,
        )
        config = {'args': args}
        events = [
            {'evid': 'ok', 'lat': 42.0, 'lon': 13.0, 'depth': 10.0},
            {'evid': 'missing-lon', 'lat': 42.1, 'lon': None, 'depth': 11.0},
        ]

        with patch(
            'seiscat.plot.plot_map.read_events_from_db',
            return_value=events,
        ):
            with patch.dict(sys.modules, {module.__name__: module}):
                output = io.StringIO()
                with redirect_stdout(output):
                    plot_catalog_map(config)

        backend.assert_called_once_with([events[0]], config)
        self.assertIn('Skipping event "missing-lon"', output.getvalue())

    def test_timeline_plotly_dispatcher_does_not_filter_coordinates(self):
        """Timeline backend should receive all events unchanged."""
        backend = MagicMock()
        module = types.ModuleType('seiscat.plot.plot_timeline_plotly')
        module.plot_catalog_timeline_plotly = backend
        args = SimpleNamespace(
            backend='plotly',
            count=True,
            colorby=None,
            colormap=None,
        )
        config = {'args': args}
        events = [
            {'evid': 'ok', 'lat': 42.0, 'lon': 13.0, 'depth': 10.0},
            {'evid': 'missing-depth', 'lat': 42.1, 'lon': 13.1, 'depth': None},
            {'evid': 'missing-lat', 'lat': None, 'lon': 13.2, 'depth': 9.0},
        ]

        with patch(
            'seiscat.plot.plot_timeline.read_events_from_db',
            return_value=events,
        ):
            with patch.dict(sys.modules, {module.__name__: module}):
                output = io.StringIO()
                with redirect_stdout(output):
                    plot_catalog_timeline(config)

        backend.assert_called_once_with(events, config)
        self.assertNotIn('Skipping event', output.getvalue())


class TestTimelineAttributeFiltering(unittest.TestCase):
    """Test timeline scatter filtering on required fields."""

    def test_skips_missing_attribute_or_colorby(self):
        """Only events with valid attribute and colorby should remain."""
        events = [
            {'evid': 'ok', 'time': 1.0, 'mag': 3.0, 'depth': 10.0},
            {'evid': 'no-attr', 'time': 2.0, 'mag': None, 'depth': 11.0},
            {'evid': 'no-color', 'time': 3.0, 'mag': 2.5, 'depth': None},
        ]

        output = io.StringIO()
        with redirect_stdout(output):
            data = get_event_times_values_and_events(
                events,
                attribute='mag',
                colorby='depth',
            )

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][2]['evid'], 'ok')
        stdout = output.getvalue()
        self.assertIn(
            'Skipping event "no-attr" for timeline plot: '
            'attribute "mag" is not defined.',
            stdout,
        )
        self.assertIn(
            'Skipping event "no-color" for timeline plot: '
            'color attribute "depth" is not defined.',
            stdout,
        )

    def test_timeline_plotly_attribute_mode_passes_events_to_backend(self):
        """Timeline dispatcher should pass events to plotly backend."""
        backend = MagicMock()
        module = types.ModuleType('seiscat.plot.plot_timeline_plotly')
        module.plot_catalog_timeline_plotly = backend
        args = SimpleNamespace(
            backend='plotly',
            count=False,
            attribute='mag',
            colorby='depth',
            colormap=None,
        )
        config = {'args': args}
        events = [
            {'evid': 'bad1', 'time': 1.0, 'mag': None, 'depth': 10.0},
            {'evid': 'bad2', 'time': 2.0, 'mag': 2.0, 'depth': None},
        ]

        with patch(
            'seiscat.plot.plot_timeline.read_events_from_db',
            return_value=events,
        ):
            with patch.dict(sys.modules, {module.__name__: module}):
                plot_catalog_timeline(config)
        backend.assert_called_once_with(events, config)


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Test station selection criteria for downloading waveforms.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import pathlib
import tempfile
import unittest
from seiscat.fetchdata.event_waveforms_utils import (
    check_station, get_picked_station_codes, get_event_layout_paths
)


class TestCheckStation(unittest.TestCase):
    """Test station code matching with wildcards."""

    def _assert_station_matches(self, pattern, matches, non_matches):
        """Assert stations that should match and not match a pattern."""
        for station in matches:
            self.assertTrue(check_station(station, pattern))
        for station in non_matches:
            self.assertFalse(check_station(station, pattern))

    def test_exact_match(self):
        """Test exact station code matching."""
        self.assertTrue(check_station('STA1', 'STA1'))
        self.assertFalse(check_station('STA2', 'STA1'))

    def test_question_mark_wildcard(self):
        """Test single-character wildcard '?'."""
        self._assert_station_matches(
            pattern='STA?',
            matches=('STA1', 'STAB'),
            non_matches=('STA12', 'ST')
        )

    def test_asterisk_wildcard(self):
        """Test multi-character wildcard '*'."""
        self._assert_station_matches(
            pattern='STA*',
            matches=('STA1', 'STATION', 'STA'),
            non_matches=('OTHER',)
        )

    def test_multiple_codes(self):
        """Test multiple station codes separated by commas."""
        self.assertTrue(check_station('STA1', 'STA1,STA2'))
        self.assertTrue(check_station('STA2', 'STA1,STA2'))
        self.assertFalse(check_station('STA3', 'STA1,STA2'))

    def test_multiple_codes_with_wildcards(self):
        """Test multiple station codes with wildcards."""
        self.assertTrue(check_station('STA1', 'STA?,OTHER*'))
        self.assertTrue(check_station('OTHERSTUFF', 'STA?,OTHER*'))
        self.assertFalse(check_station('NOPE', 'STA?,OTHER*'))

    def test_spaces_in_codes(self):
        """Test that spaces in codes are handled."""
        # Patterns with trailing/leading spaces in each code
        self.assertTrue(check_station('STA1', ' STA1 , STA2 '))
        self.assertTrue(check_station('STA2', 'STA1 , STA2'))

    def test_case_sensitive(self):
        """Test that matching is case sensitive."""
        self.assertFalse(check_station('sta1', 'STA1'))
        self.assertFalse(check_station('STA1', 'sta1'))

    def test_network_station_pattern(self):
        """Test explicit NET.STA matching when network is available."""
        self.assertTrue(check_station('ABC1', 'FR.ABC1', network='FR'))
        self.assertFalse(check_station('ABC1', 'FR.ABC1', network='IT'))

    def test_network_wildcard_pattern(self):
        """Test entire-network selection pattern like FR.*."""
        self.assertTrue(check_station('STA1', 'FR.*', network='FR'))
        self.assertFalse(check_station('STA1', 'FR.*', network='IT'))

    def test_network_pattern_backward_compatibility(self):
        """Without network info, NET.STA falls back to station-part match."""
        self.assertTrue(check_station('STA1', 'FR.STA1'))
        self.assertFalse(check_station('STA2', 'FR.STA1'))


class TestGetPickedStationCodes(unittest.TestCase):
    """Test extracting station codes with picks from QuakeML."""

    def _write_quakeml(self, tmpdir, evid, content):
        """Write a QuakeML file in tmpdir/evid/evid.xml."""
        evid_dir = pathlib.Path(tmpdir) / evid
        evid_dir.mkdir()
        xml_file = evid_dir / f'{evid}.xml'
        xml_file.write_text(content)
        return evid_dir

    def _write_quakeml_event_xml(self, tmpdir, evid, content):
        """Write a QuakeML file in tmpdir/evid/event.xml."""
        evid_dir = pathlib.Path(tmpdir) / evid
        evid_dir.mkdir()
        xml_file = evid_dir / 'event.xml'
        xml_file.write_text(content)
        return evid_dir

    def _write_quakeml_event_evid_xml(self, tmpdir, evid, content):
        """Write a QuakeML file in tmpdir/evid/event_<evid>.xml."""
        evid_dir = pathlib.Path(tmpdir) / evid
        evid_dir.mkdir()
        xml_file = evid_dir / f'event_{evid}.xml'
        xml_file.write_text(content)
        return evid_dir

    def test_no_xml_file(self):
        """Returns None when QuakeML file does not exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = pathlib.Path(tmpdir) / 'ev1'
            evid_dir.mkdir()
            result = get_picked_station_codes(evid_dir, 'ev1')
            self.assertIsNone(result)

    def test_picks_with_phase_hint(self):
        """Returns station codes from picks with P/S phase hints."""
        quakeml = """<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
    <event publicID="quakeml:test/ev1">
      <pick publicID="quakeml:test/pick/1">
        <time><value>2021-01-01T00:00:01Z</value></time>
        <waveformID networkCode="XX" stationCode="STA1" channelCode="HHZ"/>
        <phaseHint>P</phaseHint>
      </pick>
      <pick publicID="quakeml:test/pick/2">
        <time><value>2021-01-01T00:00:05Z</value></time>
        <waveformID networkCode="XX" stationCode="STA2" channelCode="HHZ"/>
        <phaseHint>S</phaseHint>
      </pick>
      <pick publicID="quakeml:test/pick/3">
        <time><value>2021-01-01T00:00:06Z</value></time>
        <waveformID networkCode="XX" stationCode="STA3" channelCode="HHZ"/>
        <phaseHint>amplitude</phaseHint>
      </pick>
      <origin publicID="quakeml:test/origin/1">
        <time><value>2021-01-01T00:00:00Z</value></time>
        <latitude><value>0.0</value></latitude>
        <longitude><value>0.0</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = self._write_quakeml(tmpdir, 'ev1', quakeml)
            result = get_picked_station_codes(evid_dir, 'ev1')
            self.assertIsNotNone(result)
            self.assertIn('STA1', result)
            self.assertIn('STA2', result)
            # STA3 has 'amplitude' phase hint, not P or S
            self.assertNotIn('STA3', result)

    def test_empty_catalog(self):
        """Returns an empty set when there are no picks."""
        quakeml = """<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
    <event publicID="quakeml:test/ev2">
      <origin publicID="quakeml:test/origin/1">
        <time><value>2021-01-01T00:00:00Z</value></time>
        <latitude><value>0.0</value></latitude>
        <longitude><value>0.0</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = self._write_quakeml(tmpdir, 'ev2', quakeml)
            result = get_picked_station_codes(evid_dir, 'ev2')
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 0)

    def test_duplicate_station_picked_twice(self):
        """Same station with both P and S picks is returned only once."""
        quakeml = """<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
    <event publicID="quakeml:test/ev3">
      <pick publicID="quakeml:test/pick/1">
        <time><value>2021-01-01T00:00:01Z</value></time>
        <waveformID networkCode="XX" stationCode="STA1" channelCode="HHZ"/>
        <phaseHint>P</phaseHint>
      </pick>
      <pick publicID="quakeml:test/pick/2">
        <time><value>2021-01-01T00:00:05Z</value></time>
        <waveformID networkCode="XX" stationCode="STA1" channelCode="HHZ"/>
        <phaseHint>S</phaseHint>
      </pick>
      <origin publicID="quakeml:test/origin/1">
        <time><value>2021-01-01T00:00:00Z</value></time>
        <latitude><value>0.0</value></latitude>
        <longitude><value>0.0</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = self._write_quakeml(tmpdir, 'ev3', quakeml)
            result = get_picked_station_codes(evid_dir, 'ev3')
            self.assertIsNotNone(result)
            self.assertEqual(result, {'STA1'})

    def test_event_xml_fallback(self):
        """Reads picks also when event file is named event.xml."""
        quakeml = """<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
    <event publicID="quakeml:test/ev4">
      <pick publicID="quakeml:test/pick/1">
        <time><value>2021-01-01T00:00:01Z</value></time>
        <waveformID networkCode="XX" stationCode="STA9" channelCode="HHZ"/>
        <phaseHint>P</phaseHint>
      </pick>
      <origin publicID="quakeml:test/origin/1">
        <time><value>2021-01-01T00:00:00Z</value></time>
        <latitude><value>0.0</value></latitude>
        <longitude><value>0.0</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = self._write_quakeml_event_xml(tmpdir, 'ev4', quakeml)
            result = get_picked_station_codes(evid_dir, 'ev4')
            self.assertEqual(result, {'STA9'})

    def test_event_evid_xml_fallback(self):
        """Reads picks when event file is named event_<evid>.xml."""
        quakeml = """<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
    <event publicID="quakeml:test/ev5">
      <pick publicID="quakeml:test/pick/1">
        <time><value>2021-01-01T00:00:01Z</value></time>
        <waveformID networkCode="XX" stationCode="STA8" channelCode="HHZ"/>
        <phaseHint>P</phaseHint>
      </pick>
      <origin publicID="quakeml:test/origin/1">
        <time><value>2021-01-01T00:00:00Z</value></time>
        <latitude><value>0.0</value></latitude>
        <longitude><value>0.0</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>"""
        with tempfile.TemporaryDirectory() as tmpdir:
            evid_dir = self._write_quakeml_event_evid_xml(
                tmpdir, 'ev5', quakeml)
            result = get_picked_station_codes(evid_dir, 'ev5')
            self.assertEqual(result, {'STA8'})


class TestFetchdataLayoutPaths(unittest.TestCase):
    """Test fetchdata layout path generation."""

    def test_event_dirs_layout_paths(self):
        """Legacy layout keeps evid.xml and subdirectories."""
        config = {
            'event_dir': '/tmp/events',
            'waveform_dir': 'waveforms',
            'station_dir': 'stations',
            'fetchdata_layout': 'event_dirs',
        }
        paths = get_event_layout_paths(config, 'ev1')
        self.assertEqual(paths['layout'], 'event_dirs')
        self.assertEqual(
            paths['event_xml_file'],
            pathlib.Path('/tmp/events/ev1/ev1.xml')
        )
        self.assertEqual(
            paths['waveform_dir'],
            pathlib.Path('/tmp/events/ev1/waveforms')
        )
        self.assertEqual(
            paths['station_dir'],
            pathlib.Path('/tmp/events/ev1/stations')
        )

    def test_event_files_layout_paths(self):
        """Bundled layout uses event_<evid>.* and stations_<evid>.xml."""
        config = {
            'event_dir': '/tmp/events',
            'waveform_dir': 'waveforms',
            'station_dir': 'stations',
            'fetchdata_layout': 'event_files',
        }
        paths = get_event_layout_paths(config, 'ev1')
        self.assertEqual(paths['layout'], 'event_files')
        self.assertEqual(
            paths['event_xml_file'],
            pathlib.Path('/tmp/events/ev1/event_ev1.xml')
        )
        self.assertEqual(
            paths['waveform_file'],
            pathlib.Path('/tmp/events/ev1/event_ev1.mseed')
        )
        self.assertEqual(
            paths['station_file'],
            pathlib.Path('/tmp/events/ev1/stations_ev1.xml')
        )


if __name__ == '__main__':
    unittest.main()

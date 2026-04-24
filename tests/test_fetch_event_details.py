# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for fetchdata event details helpers."""

import unittest
from unittest.mock import patch

from obspy.clients.fdsn.header import FDSNNoDataException

from seiscat.fetchdata.event_details import _fetch_event


class _DummyClient:
    base_url = 'http://example.test'


class TestFetchEventDetails(unittest.TestCase):
    """Unit tests for _fetch_event behavior."""

    def test_default_retries_with_raw_evid(self):
        with patch(
            'seiscat.fetchdata.event_details._get_events',
            side_effect=[FDSNNoDataException('no data'), 'ok'],
        ) as mock_get_events:
            out = _fetch_event(_DummyClient(), 'norm_id', 'raw_id')

        self.assertEqual(out, 'ok')
        self.assertEqual(
            [call.args[1] for call in mock_get_events.call_args_list],
            ['norm_id', 'raw_id']
        )

    def test_force_raw_evid_skips_normalized(self):
        calls = []

        def _fake_get_events(_client, evid):
            calls.append(evid)
            return 'ok'

        with patch(
            'seiscat.fetchdata.event_details._get_events',
            side_effect=_fake_get_events,
        ):
            out = _fetch_event(
                _DummyClient(),
                'norm_id',
                'raw_id',
                force_raw_evid=True,
            )

        self.assertEqual(out, 'ok')
        self.assertEqual(calls, ['raw_id'])

    def test_force_raw_evid_with_missing_raw_uses_normalized(self):
        calls = []

        def _fake_get_events(_client, evid):
            calls.append(evid)
            return 'ok'

        with patch(
            'seiscat.fetchdata.event_details._get_events',
            side_effect=_fake_get_events,
        ):
            out = _fetch_event(
                _DummyClient(),
                'norm_id',
                None,
                force_raw_evid=True,
            )

        self.assertEqual(out, 'ok')
        self.assertEqual(calls, ['norm_id'])


if __name__ == '__main__':
    unittest.main()

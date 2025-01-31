# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Event data types for seiscat.

:copyright:
    2022-2025 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from obspy import UTCDateTime


class Event(dict):
    """
    A custom dictionary class that supports sorting events based on keys
    and is hashable based on evid and ver.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the Event object."""
        super().__init__(*args, **kwargs)
        try:
            self['time'] = UTCDateTime(self['time'])
        except KeyError as e:
            raise KeyError('Event object must have a "time" key') from e
        # check that evid and ver are present
        if 'evid' not in self or 'ver' not in self:
            raise KeyError('Event object must have "evid" and "ver" keys')

    def __hash__(self):
        """Return a hash based on evid and ver."""
        return hash((self['evid'], self['ver']))

    def __eq__(self, other):
        """Equality comparison."""
        return self['evid'] == other['evid'] and self['ver'] == other['ver']

    def __lt__(self, other):
        """Less than comparison."""
        return self['time'] < other['time']

    def __gt__(self, other):
        """Greater than comparison."""
        return self['time'] > other['time']

    def __le__(self, other):
        """Less than or equal comparison."""
        return self['time'] <= other['time']

    def __ge__(self, other):
        """Greater than or equal comparison."""
        return self['time'] >= other['time']

    def __repr__(self):
        """Return a string representation of the Event object."""
        return f'Event({self["evid"]}, {self["ver"]})'

    def __str__(self):
        """Return a string representation of the Event object."""
        return f'{self["evid"]} ver {self["ver"]} {self["time"]}'


class EventList(list):
    """A custom list class that supports sorting events based on keys."""

    def __str__(self):
        """Return a string representation of the EventList object."""
        return '\n'.join(str(event) for event in self)

    def sort(self, key=None, reverse=False):
        """
        Sort events by a given key.

        :param key: function to sort events
        :param reverse: if True, sort in reverse
        """
        if not self:
            return
        if key is None:
            def key(event):
                return event['time'], event['ver']
        super().sort(key=key, reverse=reverse)

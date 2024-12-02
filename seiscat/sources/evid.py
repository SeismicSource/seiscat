# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Evid generation functions for seiscat.

:copyright:
    2022-2024 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
from obspy import UTCDateTime


def _base26(val):
    """
    Represent value using 6 characters from latin alphabet (26 chars).

    :param val: value to represent
    :type val: int

    :return: a string of 6 characters from latin alphabet
    :rtype: str
    """
    chars = [
      'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
      'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
      'u', 'v', 'w', 'x', 'y', 'z'
    ]
    base = len(chars)
    ret = ''
    while True:
        ret = chars[val % base] + ret
        val = val // base
        if val == 0:
            break
    return ret.rjust(6, 'a')


def generate_evid(orig_time):
    """
    Generate an event id from origin time.

    :param orig_time: origin time
    :type orig_time: obspy.UTCDateTime

    :return: an event id
    :rtype: str
    """
    prefix = 'reqk'
    year = orig_time.year
    orig_year = UTCDateTime(year=year, month=1, day=1)
    val = int(orig_time - orig_year)
    # normalize val between 0 (aaaaaa) and 26**6-1 (zzzzzz)
    maxval = 366*24*3600  # max number of seconds in leap year
    normval = int(val/maxval * (26**6-1))
    ret = _base26(normval)
    return f'{prefix}{year}{ret}'

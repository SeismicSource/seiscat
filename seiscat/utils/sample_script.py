# -*- coding: utf8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Write a sample script file for the "run" command.

:copyright:
    2022-2026 Claudio Satriano <satriano@ipgp.fr>
:license:
    GNU General Public License v3.0 or later
    (https://www.gnu.org/licenses/gpl-3.0-standalone.html)
"""
import os
from .write_ok import write_ok


SAMPLE_SCRIPT_UNIX_FILENAME = 'seiscat_run_sample.sh'
SAMPLE_SCRIPT_UNIX = f"""\
#!/usr/bin/env bash
# Sample script for the seiscat "run" command.
#
# Make sure the script is executable:
#   chmod +x {SAMPLE_SCRIPT_UNIX_FILENAME}
#
# Usage:
#   seiscat run ./{SAMPLE_SCRIPT_UNIX_FILENAME} [eventid]
#
# Environment variables provided by seiscat:
#   evid         : event id
#   time         : origin time (ISO format)
#   lat          : latitude (deg)
#   lon          : longitude (deg)
#   depth        : depth (km)
#   mag          : magnitude value
#   mag_type     : magnitude type
#   event_type   : event type
#
# Plus any user-defined database fields from the config file.

# Example: print event information
echo "  evid       = $evid"
echo "  time       = $time"
echo "  lat        = $lat"
echo "  lon        = $lon"
echo "  depth (km) = $depth"
echo "  mag        = $mag"
echo "  mag_type   = $mag_type"
echo "  event_type = $event_type"
echo

# Replace the above with your own commands to process the event.
"""

SAMPLE_SCRIPT_WINDOWS_FILENAME = 'seiscat_run_sample.bat'
SAMPLE_SCRIPT_WINDOWS = f"""\
@echo off
REM Sample script for the seiscat "run" command.
REM
REM Usage:
REM   seiscat run {SAMPLE_SCRIPT_WINDOWS_FILENAME} [eventid]
REM Environment variables provided by seiscat:
REM   evid         : event id
REM   time         : origin time (ISO format)
REM   lat          : latitude (deg)
REM   lon          : longitude (deg)
REM   depth        : depth (km)
REM   mag          : magnitude value
REM   mag_type     : magnitude type
REM   event_type   : event type
REM
REM Plus any user-defined database fields from the config file.
REM
REM Example: print event information
echo   evid       = %evid%
echo   time       = %time%
echo   lat        = %lat%
echo   lon        = %lon%
echo   depth (km) = %depth%
echo   mag        = %mag%
echo   mag_type   = %mag_type%
echo   event_type = %event_type%
echo.
REM Replace the above with your own commands to process the event.
"""


def _write_sample_script_unix():
    """
    Write a sample unix script file for the "run" command.
    """
    if not write_ok(SAMPLE_SCRIPT_UNIX_FILENAME):
        return
    with open(SAMPLE_SCRIPT_UNIX_FILENAME, 'w', encoding='utf8') as f:
        f.write(SAMPLE_SCRIPT_UNIX)
    print(f'''\
Sample script "{SAMPLE_SCRIPT_UNIX_FILENAME}" written.

Make sure the script is executable:

    chmod +x {SAMPLE_SCRIPT_UNIX_FILENAME}

Usage:

    seiscat run ./{SAMPLE_SCRIPT_UNIX_FILENAME} [eventid]
''')


def _write_sample_script_windows():
    """
    Write a sample windows script file for the "run" command.
    """
    if not write_ok(SAMPLE_SCRIPT_WINDOWS_FILENAME):
        return
    with open(SAMPLE_SCRIPT_WINDOWS_FILENAME, 'w', encoding='utf8') as f:
        f.write(SAMPLE_SCRIPT_WINDOWS)
    print(f'''\
Sample script "{SAMPLE_SCRIPT_WINDOWS_FILENAME}" written.

Usage:

    seiscat run {SAMPLE_SCRIPT_WINDOWS_FILENAME} [eventid]
''')


def write_sample_script():
    """
    Write a sample script file for the "run" command.
    """
    if os.name == 'posix':
        _write_sample_script_unix()
    elif os.name == 'nt':
        _write_sample_script_windows()
    else:
        print('Unsupported OS for sample script generation.')

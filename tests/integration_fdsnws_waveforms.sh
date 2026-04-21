#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later

set -euo pipefail

if ! command -v seiscat >/dev/null 2>&1; then
    echo "ERROR: seiscat is not available in PATH"
    exit 1
fi

TMPDIR="$(mktemp -d -t seiscat-it-fdsn-XXXXXX)"
cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

EVENT_DIR="$TMPDIR/events"
CSV_FILE="$TMPDIR/events.csv"
CONFIG_FILE="$TMPDIR/seiscat.conf"
EVID="it-live-fdsn-anmo"

cat > "$CSV_FILE" << 'EOF'
evid,time,lat,lon,depth,mag
it-live-fdsn-anmo,2024-01-01T00:00:00Z,34.9459,-106.4572,10.0,3.0
EOF

cat > "$CONFIG_FILE" << EOF
db_file = $TMPDIR/seiscat_db.sqlite
event_dir = $EVENT_DIR

start_time = None
end_time = None

fdsn_providers = IRIS

station_radius_min = 0.0
station_radius_max = 2.0
seconds_before_origin = 0
seconds_after_origin = 1800
duration_min = 0.0
interstation_distance_min = 0.0

channel_codes = "BH?,HH?,EH?"
station_codes = "AN*"
picked_stations_only = True
prefer_high_sampling_rate = False
EOF

echo "[1/4] Initializing test DB from CSV..."
seiscat initdb -c "$CONFIG_FILE" -f "$CSV_FILE"

if ! seiscat get -c "$CONFIG_FILE" evid "$EVID" >/dev/null 2>&1; then
  echo "ERROR: event $EVID not found after initdb import"
  echo "Current DB content:"
  seiscat print -c "$CONFIG_FILE" || true
    exit 1
fi

mkdir -p "$EVENT_DIR/$EVID"
cat > "$EVENT_DIR/$EVID/$EVID.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<q:quakeml xmlns="http://quakeml.org/xmlns/bed/1.2"
           xmlns:q="http://quakeml.org/xmlns/quakeml/1.2">
  <eventParameters publicID="quakeml:test/eventParameters">
  <event publicID="quakeml:test/$EVID">
      <pick publicID="quakeml:test/pick/1">
        <time><value>2024-01-01T00:00:01Z</value></time>
        <waveformID networkCode="IU" stationCode="ANMO" channelCode="BHZ"/>
        <phaseHint>P</phaseHint>
      </pick>
      <pick publicID="quakeml:test/pick/2">
        <time><value>2024-01-01T00:00:02Z</value></time>
        <waveformID networkCode="IU" stationCode="ZZZZ" channelCode="BHZ"/>
        <phaseHint>S</phaseHint>
      </pick>
      <origin publicID="quakeml:test/origin/1">
        <time><value>2024-01-01T00:00:00Z</value></time>
        <latitude><value>34.9459</value></latitude>
        <longitude><value>-106.4572</value></longitude>
      </origin>
    </event>
  </eventParameters>
</q:quakeml>
EOF

echo "[2/4] Using event ID: $EVID"

echo "[3/4] Fetching waveforms from live FDSN (IRIS)..."
seiscat fetchdata -c "$CONFIG_FILE" --data "$EVID"

WAVEFORM_DIR="$EVENT_DIR/$EVID/waveforms"
if ! ls "$WAVEFORM_DIR"/*.mseed >/dev/null 2>&1; then
    echo "ERROR: no miniSEED files downloaded in $WAVEFORM_DIR"
    exit 1
fi

echo "[4/4] Verifying station filtering (only ANMO expected)..."
bad_files="$(find "$WAVEFORM_DIR" -type f -name '*.mseed' ! -name '*.ANMO.*')"
if [[ -n "$bad_files" ]]; then
    echo "ERROR: found waveforms from unexpected stations:"
    echo "$bad_files"
    exit 1
fi

echo "OK: integration test passed. Downloaded files:"
find "$WAVEFORM_DIR" -type f -name '*.mseed' -print

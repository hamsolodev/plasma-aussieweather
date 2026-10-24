#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""List a radar station's latest loop frames and print them as JSON.

main.qml runs this through Plasma's executable engine as

    python3 -I radar.py STATION

where STATION is a BoM radar product ID such as IDR022. BoM publishes the
frame list only over anonymous FTP; the frames themselves are fetched over
https by the widget. Every outcome is one JSON object on stdout carrying
"ok"; the exit status is always 0.
"""

import ftplib
import json
import re
import sys
from datetime import datetime, timedelta, timezone

FTP_HOST = "ftp.bom.gov.au"
FTP_DIR = "/anon/gen/radar"
FRAME_URL = "https://www.bom.gov.au/radar/"
FRAME_COUNT = 6
# Older frames mean the station is down; showing them would pass off old
# rain as current. Frames from the future are allowed only clock skew.
MAX_FRAME_AGE = timedelta(hours=1)
MAX_CLOCK_SKEW = timedelta(minutes=10)
STATION = re.compile(r"IDR\d{2,3}[1-4]")


def is_station(station):
    """True for a BoM radar product ID such as IDR022."""
    return STATION.fullmatch(station) is not None


def list_names():
    """Every file name in BoM's radar directory."""
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login()
    ftp.cwd(FTP_DIR)
    names = []
    ftp.retrlines("NLST", names.append)
    ftp.quit()
    return names


def frame_names(names, station, now):
    """The station's latest frame file names, oldest first.

    The listing arrives over unencrypted FTP, so names must match BoM's
    pattern exactly (STATION.T.yyyymmddhhmm.png, UTC) to be used.
    """
    pattern = re.compile(re.escape(station) + r"\.T\.(\d{12})\.png")
    frames = []
    for name in names:
        match = pattern.fullmatch(name)
        if not match:
            continue
        try:
            taken = datetime.strptime(match.group(1), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if -MAX_CLOCK_SKEW <= now - taken <= MAX_FRAME_AGE:
            frames.append(name)
    return sorted(frames)[-FRAME_COUNT:]


def main(argv):
    station = argv[1]
    # Every result names its station: the widget drops listings for a
    # station it no longer shows.
    if not is_station(station):
        result = {"ok": False, "station": station, "error": "Not a radar station: " + station}
    else:
        try:
            now = datetime.now(timezone.utc)
            frames = [FRAME_URL + n for n in frame_names(list_names(), station, now)]
            result = {"ok": True, "station": station, "frames": frames}
        except Exception as e:
            result = {"ok": False, "station": station, "error": str(e)}
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv)

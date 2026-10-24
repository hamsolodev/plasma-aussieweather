# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""List a radar station's latest loop frames and print them as JSON.

ScriptRunner.qml runs this, for RadarSource, through Plasma's executable
engine as

    python3 -I radar.py STATION

where STATION is a BoM radar product ID such as IDR022. BoM publishes the
frame list only over anonymous FTP; the frames themselves are fetched over
https by the widget. Every outcome is one JSON object on stdout carrying
"ok"; the exit status is always 0.
"""

import ftplib
import json
import re
import resource
import signal
import sys
from datetime import UTC, datetime, timedelta

FTP_HOST = "ftp.bom.gov.au"
FTP_DIR = "/anon/gen/radar"
FRAME_URL = "https://www.bom.gov.au/radar/"
FRAME_COUNT = 6
# Older frames mean the station is down; showing them would pass off old
# rain as current. Frames from the future are allowed only clock skew.
MAX_FRAME_AGE = timedelta(hours=1)
MAX_CLOCK_SKEW = timedelta(minutes=10)
STATION = re.compile(r"IDR[0-9]{2,3}[1-4]")


# A backstop for anything else a hostile reply could make grow: the script
# runs out of memory, not the machine. It needs under 30 MB.
MEMORY_LIMIT = 512 * 1024 * 1024


def limit_memory():
    """Cap this process's address space at MEMORY_LIMIT."""
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = MEMORY_LIMIT if hard == resource.RLIM_INFINITY else min(hard, MEMORY_LIMIT)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))


def is_station(station):
    """True for a BoM radar product ID such as IDR022."""
    return STATION.fullmatch(station) is not None


# The listing comes over plain FTP, so whoever is on the network path can
# send anything, including a listing that never ends. It is capped by names,
# bytes and time; BoM's real one is about 9,000 names and 240 KB, listed in
# under 2 seconds.
MAX_NAMES = 50000
MAX_BYTES = 2 * 1024 * 1024
LISTING_DEADLINE = 30


class ListingTooLarge(Exception):
    """The listing passed MAX_NAMES or MAX_BYTES."""


class ListingTimedOut(Exception):
    """The listing took longer than LISTING_DEADLINE."""


class BoundedFTP(ftplib.FTP):
    """ftplib's client, refusing a multi-line reply longer than
    MAX_REPLY_LINES. On the plain connection anyone on the path can write
    the replies, and ftplib joins a multi-line one without limit (it caps
    only each line's length)."""

    MAX_REPLY_LINES = 100

    def getmultiline(self):
        line = self.getline()
        if line[3:4] != "-":
            return line
        code = line[:3]
        for _ in range(self.MAX_REPLY_LINES):
            next_line = self.getline()
            line = line + "\n" + next_line
            if next_line[:3] == code and next_line[3:4] != "-":
                return line
        raise ListingTooLarge()


class NameCollector:
    """Collects an NLST listing's names, refusing an endless one."""

    def __init__(self):
        self.names = []
        self.size = 0

    def __call__(self, name):
        self.size += len(name) + 2
        if len(self.names) >= MAX_NAMES or self.size > MAX_BYTES:
            raise ListingTooLarge()
        self.names.append(name)


def list_names():
    """Every file name in BoM's radar directory."""
    collect = NameCollector()
    ftp = BoundedFTP(FTP_HOST, timeout=15)
    try:
        ftp.login()
        ftp.cwd(FTP_DIR)
        ftp.retrlines("NLST", collect)
    finally:
        ftp.close()
    return collect.names


def listing_failure(error):
    """ERROR, from listing the directory, as words fit to show. An FTP
    server's reply text is left out: on a plain connection, anyone on the
    path can write it."""
    if isinstance(error, ListingTimedOut):
        return "listing took too long"
    if isinstance(error, ListingTooLarge):
        return "listing too large"
    if isinstance(error, ftplib.Error):
        code = re.match(r"[0-9]{3}", str(error))
        return "FTP reply " + code.group(0) if code else "FTP error"
    if isinstance(error, EOFError):
        return "connection closed"
    return str(error)


def _deadline_passed(signum, frame):
    raise ListingTimedOut()


def frame_names(names, station, now):
    """The station's latest frame file names, oldest first.

    The listing arrives over unencrypted FTP, so names must match BoM's
    pattern exactly (STATION.T.yyyymmddhhmm.png, UTC) to be used.
    """
    pattern = re.compile(re.escape(station) + r"\.T\.([0-9]{12})\.png")
    frames = []
    for name in names:
        match = pattern.fullmatch(name)
        if not match:
            continue
        try:
            taken = datetime.strptime(match.group(1), "%Y%m%d%H%M").replace(tzinfo=UTC)
        except ValueError:
            continue
        if -MAX_CLOCK_SKEW <= now - taken <= MAX_FRAME_AGE:
            frames.append(name)
    return sorted(frames)[-FRAME_COUNT:]


def listing(station, now):
    """The JSON-ready result for STATION: its frame URLs, or a failure.

    A failure has a kind the widget words for the user: invalid_station
    (permanent), no_frames (the station is offline or not yet updated) or
    network (the listing could not be fetched).
    """
    if not is_station(station):
        return {"ok": False, "error": "invalid_station", "detail": station, "permanent": True}
    # A per-read timeout never trips while data keeps trickling in, so the
    # whole listing has a deadline.
    previous = signal.signal(signal.SIGALRM, _deadline_passed)
    signal.alarm(LISTING_DEADLINE)
    try:
        names = list_names()
    except (OSError, EOFError, ftplib.Error, ListingTooLarge, ListingTimedOut) as e:
        return {"ok": False, "error": "network", "detail": listing_failure(e), "permanent": False}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    frames = frame_names(names, station, now)
    if not frames:
        return {"ok": False, "error": "no_frames", "detail": station, "permanent": False}
    return {"ok": True, "frames": [FRAME_URL + n for n in frames]}


def main(argv):
    station = argv[1]
    result = listing(station, datetime.now(UTC))
    # Every result names its station: the widget drops listings for a
    # station it no longer shows.
    result["station"] = station
    print(json.dumps(result))


if __name__ == "__main__":
    limit_memory()
    main(sys.argv)

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
import sys

FTP_HOST = "ftp.bom.gov.au"
FTP_DIR = "/anon/gen/radar"
FRAME_URL = "https://www.bom.gov.au/radar/"
FRAME_COUNT = 6


def list_names():
    """Every file name in BoM's radar directory."""
    ftp = ftplib.FTP(FTP_HOST, timeout=15)
    ftp.login()
    ftp.cwd(FTP_DIR)
    names = []
    ftp.retrlines("NLST", names.append)
    ftp.quit()
    return names


def frame_names(names, station):
    """The station's latest frame file names, oldest first."""
    prefix = station + ".T."
    return sorted(n for n in names if n.startswith(prefix) and n.endswith(".png"))[-FRAME_COUNT:]


def main(argv):
    station = argv[1]
    try:
        frames = [FRAME_URL + n for n in frame_names(list_names(), station)]
        result = {"ok": True, "frames": frames}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv)

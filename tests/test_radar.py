# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import contextlib
import ftplib
import io
import json
import time
import unittest
from datetime import datetime, timezone

from codeloader import load

radar = load("radar")

NOW = datetime(2026, 10, 24, 1, 0, tzinfo=timezone.utc)


def frame(minute, station="IDR022"):
    """A frame name taken MINUTE minutes past midnight UTC on 2026-10-24."""
    return "%s.T.20261024%02d%02d.png" % (station, minute // 60, minute % 60)


class FrameNamesTest(unittest.TestCase):

    def test_latest_frames_of_the_station_oldest_first(self):
        names = [frame(m) for m in range(0, 60, 6)]
        names += [frame(54, "IDR023"), "IDR022.gif", "IDR02.T.202610240054.png"]
        self.assertEqual(radar.frame_names(names, "IDR022", NOW),
                         [frame(m) for m in range(24, 60, 6)])

    def test_names_must_match_exactly(self):
        names = [frame(30),
                 frame(31) + ".png",
                 "IDR022.T.202610240032.png/../../IDR023.T.202610240032.png",
                 "IDR022.T.2026102400333.png",
                 "xIDR022.T.202610240034.png"]
        self.assertEqual(radar.frame_names(names, "IDR022", NOW), [frame(30)])

    def test_frames_older_than_an_hour_are_dropped(self):
        names = ["IDR022.T.202610232359.png", frame(0), frame(30)]
        self.assertEqual(radar.frame_names(names, "IDR022", NOW), [frame(0), frame(30)])

    def test_impossible_and_future_timestamps_are_dropped(self):
        names = [frame(30), "IDR022.T.202613240030.png", "IDR022.T.202610240130.png"]
        self.assertEqual(radar.frame_names(names, "IDR022", NOW), [frame(30)])


def run_main(station, names):
    """radar.main's JSON output, with the FTP listing answered by NAMES.

    NAMES may be an exception instance, raised by the listing instead.
    """
    def list_names():
        if isinstance(names, Exception):
            raise names
        if callable(names):
            return names()
        return names

    original = radar.list_names
    radar.list_names = list_names
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            radar.main(["radar.py", station])
        return json.loads(out.getvalue())
    finally:
        radar.list_names = original


class MainTest(unittest.TestCase):

    def test_frames_are_https_urls_naming_their_station(self):
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        result = run_main("IDR022", ["IDR022.T.%s.png" % now])
        self.assertEqual(result, {"ok": True, "station": "IDR022",
                                  "frames": ["https://www.bom.gov.au/radar/IDR022.T.%s.png" % now]})

    def test_invalid_station_is_permanent_and_lists_nothing(self):
        result = run_main("IDR02;x", AssertionError("listed"))
        self.assertEqual((result["ok"], result["station"], result["error"], result["permanent"]),
                         (False, "IDR02;x", "invalid_station", True))

    def test_no_recent_frames_is_a_failure(self):
        result = run_main("IDR022", ["IDR022.T.202001010000.png"])
        self.assertEqual((result["ok"], result["error"], result["permanent"]),
                         (False, "no_frames", False))

    def test_server_text_is_not_shown(self):
        # The listing is plain FTP: whoever is on the path writes the reply.
        refusal = ftplib.error_perm("530 BoM radar access suspended. Call 1800-000-000")
        result = run_main("IDR022", refusal)
        self.assertEqual((result["error"], result["detail"]), ("network", "FTP reply 530"))

    def test_listing_has_a_deadline(self):
        original = radar.LISTING_DEADLINE
        radar.LISTING_DEADLINE = 1
        try:
            started = time.monotonic()
            result = run_main("IDR022", lambda: time.sleep(10))
        finally:
            radar.LISTING_DEADLINE = original
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual((result["error"], result["detail"]), ("network", "listing took too long"))

    def test_listing_failure_is_a_network_failure(self):
        result = run_main("IDR022", ConnectionRefusedError(111, "Connection refused"))
        self.assertEqual((result["ok"], result["error"], result["permanent"]),
                         (False, "network", False))
        self.assertIn("Connection refused", result["detail"])


class NameCollectorTest(unittest.TestCase):

    def test_collects_names(self):
        collect = radar.NameCollector()
        collect("IDR022.T.202610240000.png")
        self.assertEqual(collect.names, ["IDR022.T.202610240000.png"])

    def test_endless_listing_is_cut_off(self):
        collect = radar.NameCollector()
        with self.assertRaises(radar.ListingTooLarge):
            for _ in range(radar.MAX_NAMES + 1):
                collect("x")
        collect = radar.NameCollector()
        with self.assertRaises(radar.ListingTooLarge):
            for _ in range(radar.MAX_BYTES // 100 + 1):
                collect("x" * 100)


class StationTest(unittest.TestCase):

    def test_valid_station_ids(self):
        for station in ("IDR022", "IDR644", "IDR1141"):
            self.assertTrue(radar.is_station(station), station)

    def test_invalid_station_ids(self):
        for station in ("", "IDR02", "IDR025", "IDR02.T", "IDR022 ", "../IDR022", "idr022", "IDR٠٢2"):
            self.assertFalse(radar.is_station(station), station)


if __name__ == "__main__":
    unittest.main()

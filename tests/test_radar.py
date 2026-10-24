# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

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


class StationTest(unittest.TestCase):

    def test_valid_station_ids(self):
        for station in ("IDR022", "IDR644", "IDR1141"):
            self.assertTrue(radar.is_station(station), station)

    def test_invalid_station_ids(self):
        for station in ("", "IDR02", "IDR025", "IDR02.T", "IDR022 ", "../IDR022", "idr022"):
            self.assertFalse(radar.is_station(station), station)


if __name__ == "__main__":
    unittest.main()

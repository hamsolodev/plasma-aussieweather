# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest

from codeloader import load

radar = load("radar")


class FrameNamesTest(unittest.TestCase):

    def test_latest_frames_of_the_station_oldest_first(self):
        names = ["IDR022.T.2026102400%02d.png" % m for m in range(0, 60, 6)]
        names += ["IDR023.T.202610240054.png", "IDR022.gif", "IDR02.T.202610240054.png"]
        frames = radar.frame_names(names, "IDR022")
        self.assertEqual(frames, ["IDR022.T.2026102400%02d.png" % m for m in range(24, 60, 6)])


if __name__ == "__main__":
    unittest.main()

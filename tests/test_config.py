# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The config schema (main.xml) agrees with the code that reads it."""

import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

CONTENTS = pathlib.Path(__file__).resolve().parent.parent / "contents"
KCFG = "{http://www.kde.org/standards/kcfg/1.0}"


def defaults():
    """{entry name: default text} from main.xml."""
    root = ET.parse(CONTENTS / "config" / "main.xml").getroot()
    return {entry.get("name"): (entry.findtext(KCFG + "default") or "")
            for entry in root.iter(KCFG + "entry")}


class ConfigDefaultsTest(unittest.TestCase):

    def test_radar_station_default_matches_radarstations(self):
        source = (CONTENTS / "ui" / "radarstations.js").read_text()
        default_id = re.search(r'^var defaultId = "([^"]+)"', source, re.MULTILINE)
        self.assertIsNotNone(default_id, "defaultId not found in radarstations.js")
        self.assertEqual(defaults()["radarStation"], default_id.group(1))


if __name__ == "__main__":
    unittest.main()

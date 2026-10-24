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

    def test_the_settings_page_declares_only_config_entries(self):
        # Plasma fills a cfg_ property from the entry of that name: one with
        # no entry is never loaded or saved.
        page = (CONTENTS / "ui" / "ConfigPage.qml").read_text()
        declared = set(re.findall(r"^\s*property\s+\w+\s+cfg_(\w+)", page, re.MULTILINE))
        self.assertTrue(declared, "no cfg_ properties found in ConfigPage.qml")
        self.assertLessEqual(declared, set(defaults()))

    def test_no_place_is_saved_by_default(self):
        self.assertEqual(defaults()["places"], "")


if __name__ == "__main__":
    unittest.main()

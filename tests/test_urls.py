# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Nothing in the widget package fetches or links over plain http.

An image fetched over http can be swapped in transit for any bytes, which
Qt then hands to whichever decoder sniffs them.
"""

import pathlib
import unittest

CONTENTS = pathlib.Path(__file__).resolve().parent.parent / "contents"


class UrlSchemeTest(unittest.TestCase):
    def test_no_plain_http_urls(self):
        examined = 0
        found = []
        for path in sorted(CONTENTS.rglob("*")):
            if path.suffix not in (".qml", ".js", ".py"):
                continue
            examined += 1
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if "http://" in line:
                    found.append(f"{path.relative_to(CONTENTS)}:{number}")
        self.assertGreater(examined, 0, "no files scanned — is the path right?")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()

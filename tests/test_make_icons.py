# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""scripts/make-icons.py --check fails on each way an icon copy can go
stale or wrong. Standard library only: the PNGs here are made by hand."""

import hashlib
import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zlib

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "make-icons.py"
spec = importlib.util.spec_from_file_location("make_icons", SCRIPT)
make_icons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_icons)


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def png(edge, stamp=None, colour=6):
    """A blank PNG EDGE pixels square, of PNG colour type COLOUR, recording
    STAMP as its source's hash."""
    channels = {2: 3, 6: 4}[colour]
    rows = b"".join(b"\0" + bytes(edge * channels) for _ in range(edge))
    text = chunk(b"tEXt", make_icons.STAMP_KEY.encode() + b"\0" + stamp.encode()) if stamp else b""
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", edge, edge, 8, colour, 0, 0, 0))
        + text
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name)
        for key, path in make_icons.SOURCES.items():
            self.write(path, (f'<svg id="{key}"/>').encode())
        for path, key in make_icons.SVG_COPIES.items():
            self.write(path, self.source(key))
        for path, (key, edge) in make_icons.PNGS.items():
            self.write(path, png(edge, self.sha(key)))

    def tearDown(self):
        self.directory.cleanup()

    def write(self, path, data):
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_bytes(data)

    def source(self, key):
        return (self.root / make_icons.SOURCES[key]).read_bytes()

    def sha(self, key):
        return hashlib.sha256(self.source(key)).hexdigest()

    def problems(self):
        examined, problems = make_icons.check(self.root)
        self.assertEqual(examined, len(make_icons.SVG_COPIES) + len(make_icons.PNGS))
        return problems

    def test_current_targets_pass(self):
        self.assertEqual(self.problems(), [])

    def test_a_source_changed_without_remaking(self):
        self.write("branding/icon.svg", b'<svg id="changed"/>')
        self.assertEqual(
            len([p for p in self.problems() if "not today's branding/icon.svg" in p]),
            sum(key == "icon" for key, _ in make_icons.PNGS.values()),
        )

    def test_a_png_made_from_the_other_source(self):
        self.write("contents/screenshot.png", png(256, self.sha("small")))
        self.assertEqual(
            self.problems(),
            [
                (
                    "contents/screenshot.png: made from "
                    "branding/icon-small.svg, not today's branding/icon.svg"
                )
            ],
        )

    def test_a_png_not_made_by_the_script(self):
        self.write("docs/icon.png", png(256))
        self.assertEqual(
            self.problems(),
            [("docs/icon.png: made from an unrecorded source, not today's branding/icon.svg")],
        )

    def test_the_wrong_size(self):
        self.write("contents/screenshot.png", png(128, self.sha("icon")))
        self.assertEqual(self.problems(), ["contents/screenshot.png: 128x128, wants 256x256"])

    def test_corners_that_are_not_transparent(self):
        self.write("docs/icon.png", png(256, self.sha("icon"), colour=2))
        self.assertEqual(len(self.problems()), 1)
        self.assertIn("no alpha channel", self.problems()[0])

    def test_a_stale_svg_copy(self):
        self.write("docs/favicon.svg", b'<svg id="old"/>')
        self.assertEqual(
            self.problems(), ["docs/favicon.svg: differs from branding/icon-small.svg"]
        )

    def test_a_missing_target(self):
        (self.root / "contents/screenshot.png").unlink()
        self.assertEqual(self.problems(), ["contents/screenshot.png: missing"])

    def test_not_a_png(self):
        self.write("docs/icon.png", b"GIF89a")
        self.assertEqual(self.problems(), ["docs/icon.png: not a PNG"])


if __name__ == "__main__":
    unittest.main()

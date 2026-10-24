# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Every text element in the widget's QML states its textFormat.

The default, AutoText, renders a string that opens with a tag as styled
text and loads any <img> in it — and nearly every string the widget shows
comes from the BoM API. PlainLabel sets PlainText once; any other text
element must say what it renders.
"""

import pathlib
import re
import unittest

UI = pathlib.Path(__file__).resolve().parent.parent / "contents" / "ui"

TEXT_ELEMENT = re.compile(
    r"^\s*(PlasmaComponents\.(?:Label|ToolTip)|QQC2\.(?:Label|ToolTip)"
    r"|Kirigami\.(?:Heading|SelectableLabel)|Text|TextEdit)\s*\{")


def own_lines(lines, start):
    """The lines of the block opened on lines[start], at its own depth only."""
    depth = 0
    for line in lines[start:]:
        if depth == 1:
            yield line
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            return


def text_elements(path):
    """(line number, element, states textFormat?) for each text element."""
    lines = path.read_text().splitlines()
    for number, line in enumerate(lines):
        match = TEXT_ELEMENT.match(line)
        if match:
            stated = any(re.match(r"\s*textFormat\s*:", l) for l in own_lines(lines, number))
            yield number + 1, match.group(1), stated


class TextFormatTest(unittest.TestCase):

    def test_every_text_element_states_its_format(self):
        examined = []
        unstated = []
        for path in sorted(UI.glob("*.qml")):
            for number, element, stated in text_elements(path):
                examined.append(element)
                if not stated:
                    unstated.append("%s:%d %s" % (path.name, number, element))
        self.assertGreater(len(examined), 0, "no text elements found — is the scan broken?")
        self.assertEqual(unstated, [], "text elements without textFormat (use PlainLabel)")

    def test_labels_use_plain_label(self):
        used = sum(path.read_text().count("PlainLabel {") for path in UI.glob("*.qml"))
        self.assertGreater(used, 0)


if __name__ == "__main__":
    unittest.main()

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Every text element in the widget's QML renders plain text.

Qt's default, AutoText, renders a string that opens with a tag as styled
text and loads any <img> in it, and nearly every string the widget shows
comes from the BoM API. So:

- an element that has a textFormat states Text.PlainText, except the one
  sanitised warning body (WarningsTab.qml), which is RichText;
- PlainLabel, and the types built on it, never override its textFormat;
- Kirigami.InlineMessage, which has no textFormat (it shows its text in a
  SelectableLabel), is given only translated string literals.

Comments and string literals are blanked before checking, so neither can
satisfy or dodge a rule.
"""

import pathlib
import re
import tempfile
import unittest

UI = pathlib.Path(__file__).resolve().parent.parent / "contents" / "ui"

# Types with a textFormat property that show text.
TEXT_TYPES = {
    "Text", "TextEdit", "Label", "ToolTip", "TextArea",
    "PlasmaComponents.Label", "PlasmaComponents.ToolTip", "PlasmaComponents.TextArea",
    "QQC2.Label", "QQC2.ToolTip", "QQC2.TextArea",
    "Kirigami.Heading", "Kirigami.SelectableLabel", "PlasmaExtras.Heading",
}
CONSTANT_TEXT_TYPES = {"Kirigami.InlineMessage", "InlineMessage"}
# The one element allowed to render RichText: the warning body, which
# poll.py's allowlist has already rebuilt.
RICH_TEXT_FILE = "WarningsTab.qml"
RICH_TEXT_BINDING = "text: modelData.html"

DECLARATION = re.compile(r"(?<![\w.])((?:[A-Za-z_]\w*\.)?[A-Z]\w*)\s*\{")


def blank_comments_and_strings(source):
    """SOURCE with comments removed and each string literal replaced by S."""
    out = []
    i = 0
    while i < len(source):
        if source.startswith("//", i):
            i = source.find("\n", i)
            i = len(source) if i < 0 else i
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = len(source) if end < 0 else end + 2
        elif source[i] in "\"'`":
            quote = source[i]
            i += 1
            while i < len(source) and source[i] != quote:
                i += 2 if source[i] == "\\" else 1
            i += 1
            out.append("S")
        else:
            out.append(source[i])
            i += 1
    return "".join(out)


def own_bindings(code, open_brace):
    """The text of the block opened at code[open_brace], at its own depth:
    nested blocks (child objects, JS blocks) left out."""
    depth = 0
    out = []
    for i in range(open_brace, len(code)):
        char = code[i]
        if char == "{":
            depth += 1
            if depth == 1:
                continue
        elif char == "}":
            depth -= 1
            if depth == 0:
                break
        if depth == 1:
            out.append(char)
    return "".join(out)


def declarations(path):
    """(type, own bindings) for every object declared in PATH."""
    code = blank_comments_and_strings(path.read_text())
    for match in DECLARATION.finditer(code):
        yield match.group(1), own_bindings(code, match.end() - 1)


def root_type(path):
    code = blank_comments_and_strings(path.read_text())
    match = DECLARATION.search(code)
    return match.group(1) if match else None


def plain_label_types(ui):
    """PlainLabel and the types in UI built on it, however indirectly."""
    roots = {path.stem: root_type(path) for path in ui.glob("*.qml")}
    found = {"PlainLabel"}
    while True:
        more = {name for name, root in roots.items() if root in found} - found
        if not more:
            return found
        found |= more


def binding(bindings, name):
    """The expression bound to NAME, read on past line ends while brackets
    are open; None if NAME is not bound."""
    match = re.search(r"(?:^|[;\n])\s*" + name + r"\s*:", bindings)
    if not match:
        return None
    depth = 0
    out = []
    for char in bindings[match.end():]:
        if char in ";\n" and depth == 0:
            break
        depth += (char in "([") - (char in ")]")
        out.append(char)
    return "".join(out).strip()


def check(ui):
    """(elements examined, rich-text exemptions used, problems) for UI."""
    plain = plain_label_types(ui)
    examined = 0
    exemptions = 0
    problems = []
    for path in sorted(ui.glob("*.qml")):
        for kind, bindings in declarations(path):
            where = "%s %s" % (path.name, kind)
            text_format = binding(bindings, "textFormat")
            if kind in plain and path.stem != kind:
                examined += 1
                if text_format is not None:
                    problems.append(where + " overrides PlainLabel's textFormat")
            elif kind in TEXT_TYPES:
                examined += 1
                if text_format == "Text.PlainText":
                    continue
                rich_ok = (text_format == "Text.RichText" and path.name == RICH_TEXT_FILE
                           and RICH_TEXT_BINDING in bindings)
                if rich_ok:
                    exemptions += 1
                else:
                    problems.append("%s textFormat is %s" % (where, text_format or "unstated"))
            elif kind in CONSTANT_TEXT_TYPES:
                examined += 1
                text = re.sub(r"\s", "", binding(bindings, "text") or "")
                if not re.fullmatch(r"(i18nc?\(S(\+S)*(,S(\+S)*)?\)\+?)+", text):
                    problems.append(where + " text is not translated literals only")
    return examined, exemptions, problems


class TextFormatTest(unittest.TestCase):

    def test_every_text_element_renders_plain_text(self):
        examined, exemptions, problems = check(UI)
        self.assertGreater(examined, 30, "too few text elements found: is the scan broken?")
        self.assertEqual(problems, [])
        self.assertEqual(exemptions, 1, "exactly one RichText element: the warning body")


class CheckerTest(unittest.TestCase):
    """The checker catches what it is for: each way a string could end up
    rendered as markup, added to a copy of the real UI."""

    INJECTED = {
        "inline delegate":       "Repeater { delegate: PlasmaComponents.Label { text: w.title } }",
        "styled PlainLabel":     "PlainLabel { textFormat: Text.StyledText; text: w.title }",
        "AutoText":              "Text { textFormat: Text.AutoText; text: w.title }",
        "format in a comment":   "Text { /* textFormat: Text.PlainText */ text: w.title }",
        "format in a string":    "Text { text: \"textFormat: Text.PlainText\" + w.title }",
        "contentItem":           "Item { property Item contentItem: Text { text: w.title } }",
        "bare Label":            "Label { text: w.title }",
        "rich text elsewhere":   "Text { textFormat: Text.RichText; text: w.title }",
        "message from data":     "Kirigami.InlineMessage { text: w.title }",
    }

    # A whole file: a new type built on PlainLabel that undoes it.
    INJECTED_FILES = {
        "type built on PlainLabel": "PlainLabel { textFormat: Text.StyledText }",
    }

    def caught(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            ui = pathlib.Path(tmp)
            for path in UI.glob("*.qml"):
                (ui / path.name).write_text(path.read_text())
            (ui / "Injected.qml").write_text(source)
            _, _, problems = check(ui)
            return any(p.startswith("Injected.qml") for p in problems)

    def test_each_injection_is_caught(self):
        for name, snippet in self.INJECTED.items():
            with self.subTest(name):
                self.assertTrue(self.caught("Item {\n    " + snippet + "\n}\n"), snippet)
        for name, source in self.INJECTED_FILES.items():
            with self.subTest(name):
                self.assertTrue(self.caught(source + "\n"), source)


if __name__ == "__main__":
    unittest.main()

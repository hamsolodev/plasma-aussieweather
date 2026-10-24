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
  SelectableLabel), and Kirigami.FormData.label are given only translated
  string literals;
- textFormat is never set any other way: imperatively, or through a
  Binding or PropertyChanges.

Types are matched under the import names below, whatever alias a file
gives a module.

Comments and string literals are blanked before checking, so neither can
satisfy or dodge a rule.
"""

import pathlib
import re
import tempfile
import unittest

UI = pathlib.Path(__file__).resolve().parent.parent / "contents" / "ui"

# The import name each module's types are matched under.
MODULE_NAMES = {
    "QtQuick": "",
    "QtQuick.Controls": "QQC2",
    "QtQuick.Controls.Basic": "QQC2",
    "QtQuick.Templates": "QQC2",
    "org.kde.plasma.components": "PlasmaComponents",
    "org.kde.plasma.extras": "PlasmaExtras",
    "org.kde.plasma.core": "PlasmaCore",
    "org.kde.kirigami": "Kirigami",
}
IMPORT = re.compile(r"^\s*import\s+([\w.]+)(?:\s+[\d.]+)?\s+as\s+(\w+)", re.MULTILINE)

# Types with a textFormat property that show text.
TEXT_TYPES = {
    "Text", "TextEdit", "Label", "ToolTip", "TextArea",
    "PlasmaComponents.Label", "PlasmaComponents.ToolTip", "PlasmaComponents.TextArea",
    "QQC2.Label", "QQC2.ToolTip", "QQC2.TextArea",
    "Kirigami.Heading", "Kirigami.SelectableLabel", "Kirigami.LinkButton",
    "Kirigami.UrlButton", "PlasmaExtras.Heading", "PlasmaExtras.DescriptiveLabel",
    "PlasmaCore.ToolTipArea",
}
CONSTANT_TEXT_TYPES = {
    "Kirigami.InlineMessage", "InlineMessage", "Kirigami.ListSectionHeader",
    "Kirigami.PlaceholderMessage", "Kirigami.Chip",
}
# Controls draw their labels as AutoText, which cannot be changed: their
# text must be translated (i18n), never data.
BUTTON_TYPES = {
    "Button", "TabButton", "ToolButton", "ItemDelegate",
    "QQC2.Button", "QQC2.TabButton", "QQC2.ToolButton", "QQC2.ItemDelegate",
    "PlasmaComponents.Button", "PlasmaComponents.TabButton", "PlasmaComponents.ToolButton",
    "PlasmaComponents.ItemDelegate",
}
TRANSLATED_CALL = re.compile(r"i18n[cp]*\(S.*\)")
TRANSLATED_LITERALS = re.compile(r"(i18nc?\(S(\+S)*(,S(\+S)*)?\)\+?)+")
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


def canonical(kind, aliases):
    """KIND with its import alias replaced by the name in MODULE_NAMES."""
    prefix, dot, name = kind.rpartition(".")
    if not dot:
        return kind
    module = aliases.get(prefix, prefix)
    return module + "." + name if module else name


def import_aliases(source):
    """{alias: name in MODULE_NAMES} for the imports in SOURCE."""
    return {alias: MODULE_NAMES.get(module, alias) for module, alias in IMPORT.findall(source)}


def declarations(path):
    """(type, own bindings) for every object declared in PATH."""
    source = path.read_text()
    aliases = import_aliases(source)
    code = blank_comments_and_strings(source)
    for match in DECLARATION.finditer(code):
        yield canonical(match.group(1), aliases), own_bindings(code, match.end() - 1)


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
    match = re.search(r"(?:^|[;\n])\s*" + re.escape(name) + r"\s*:", bindings)
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
        source = path.read_text()
        code = blank_comments_and_strings(source)
        kirigami_aliases = ["Kirigami"] + [a for a, m in import_aliases(source).items()
                                           if m == "Kirigami" and a != "Kirigami"]
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
                if not TRANSLATED_LITERALS.fullmatch(text):
                    problems.append(where + " text is not translated literals only")
            elif kind in BUTTON_TYPES:
                examined += 1
                text = re.sub(r"\s", "", binding(bindings, "text") or "")
                if text and not TRANSLATED_CALL.fullmatch(text):
                    problems.append(where + " text is not translated")
            elif kind == "PropertyChanges" and text_format is not None:
                problems.append(where + " sets textFormat")
            for alias in kirigami_aliases:
                label = binding(bindings, alias + ".FormData.label")
                if label is not None:
                    examined += 1
                    if not TRANSLATED_LITERALS.fullmatch(re.sub(r"\s", "", label)):
                        problems.append(where + " FormData.label is not translated literals only")
        if re.search(r"textFormat\s*=(?!=)", code):
            problems.append(path.name + " assigns textFormat in script")
        if re.search(r"""property\s*:\s*["']textFormat["']""", source):
            problems.append(path.name + " binds textFormat through a Binding")
        if re.search(r"""\[\s*["']textFormat["']\s*\]""", source):
            problems.append(path.name + " reaches textFormat by name")
        if re.search(r"\balias\s+\w+\s*:\s*[\w.]*\btextFormat\b", code):
            problems.append(path.name + " aliases a textFormat")
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
        # The second review's forms.
        "descriptive label":     "PlasmaExtras.DescriptiveLabel { text: w.title }",
        "link button":           "Kirigami.LinkButton { text: w.title }",
        "tooltip area":          "PlasmaCore.ToolTipArea { mainText: w.title }",
        "form label from data":  "Item { Kirigami.FormData.label: w.title }",
        "imperative format":     "PlainLabel { Component.onCompleted: textFormat = Text.StyledText }",
        "Binding":               "Binding { target: x; property: \"textFormat\"; value: Text.AutoText }",
        "PropertyChanges":       "PropertyChanges { target: x; textFormat: Text.AutoText }",
        # The third review's forms.
        "alias property":        "Item { property alias f: x.textFormat }",
        "set by name":           "Item { Component.onCompleted: x[\"textFormat\"] = 4 }",
        "section header":        "Kirigami.ListSectionHeader { text: w.title }",
        "button with data":      "PlasmaComponents.Button { text: w.title }",
    }

    # Under an alias the module's types must still be recognised.
    INJECTED_ALIASED = {
        "PC.Label": "import org.kde.plasma.components as PC\nItem { PC.Label { text: w.title } }\n",
        "QQ.Text": "import QtQuick as QQ\nQQ.Item { QQ.Text { text: w.title } }\n",
        "Basic": "import QtQuick.Controls.Basic as B\nItem { B.Label { text: w.title } }\n",
        "K.FormData": "import org.kde.kirigami as K\nItem { Item { K.FormData.label: w.title } }\n",
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
        for name, source in self.INJECTED_ALIASED.items():
            with self.subTest(name):
                self.assertTrue(self.caught(source), source)


if __name__ == "__main__":
    unittest.main()

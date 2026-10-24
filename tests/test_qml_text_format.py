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
- the PlasmoidItem's tooltip states Text.PlainText;
- library types that draw their own text, as AutoText or with no
  textFormat to set (buttons, tabs, menu items, actions, Kirigami's
  messages and headers), and the attached FormData.label and ToolTip.text,
  are given only translated string literals, whose only arguments are
  counts (".length");
- textFormat is named nowhere else: not in script, an alias, a Binding,
  a PropertyChanges or a string.

Types are matched by name alone, whatever module or alias they come from.
ComboBox models are not checked: the widget's come from its own tables.

Comments and string literals are blanked before checking, so neither can
satisfy or dodge a rule. scripts/render.py checks every text item the
widget declares as it is built, which catches what a source check misses.
"""

import pathlib
import re
import tempfile
import unittest

UI = pathlib.Path(__file__).resolve().parent.parent / "contents" / "ui"

# Types with a textFormat property that show text.
TEXT_TYPES = {
    "Text", "TextEdit", "Label", "ToolTip", "TextArea", "Heading", "SelectableLabel",
    "LinkButton", "UrlButton", "DescriptiveLabel", "ToolTipArea",
}
# Library types that draw their own text, as AutoText or with no textFormat
# to set, and the properties they draw it from.
SELF_DRAWN_TYPES = {
    "Button", "TabButton", "ToolButton", "RoundButton", "DelayButton", "CheckBox",
    "RadioButton", "Switch", "ItemDelegate", "CheckDelegate", "RadioDelegate",
    "SwitchDelegate", "SwipeDelegate", "MenuItem", "Action", "GroupBox",
    "InlineMessage", "ListSectionHeader", "PlaceholderMessage", "Chip",
}
SELF_DRAWN_PROPERTIES = ("text", "title", "explanation")
# Attached properties drawn as AutoText.
ATTACHED_TEXT = (r"(?:\w+\.)*FormData\.label", r"(?:\w+\.)*ToolTip\.text")
# i18n calls on string literals, whose only other arguments are counts.
_LITERALS = r"S(?:\+S)*"
_CALL = r"i18n[cp]*\(%s(?:,%s)*(?:,[\w.]+\.length)*\)" % (_LITERALS, _LITERALS)
TRANSLATED = re.compile(r"%s(?:\+%s)*" % (_CALL, _CALL))
FORMAT_NAMES = re.compile(r"\b(?:textFormat|toolTipTextFormat)\b")
FORMAT_STRING = re.compile(r"""(["'`])\s*(?:textFormat|toolTipTextFormat)\s*\1""")
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


def type_name(kind):
    """KIND without its module or alias: "Kirigami.Heading" is Heading."""
    return kind.rpartition(".")[2]


def declarations(path):
    """(type name, own bindings) for every object declared in PATH."""
    code = blank_comments_and_strings(path.read_text())
    for match in DECLARATION.finditer(code):
        yield type_name(match.group(1)), own_bindings(code, match.end() - 1)


def root_type(path):
    code = blank_comments_and_strings(path.read_text())
    match = DECLARATION.search(code)
    return type_name(match.group(1)) if match else None


def plain_label_types(ui):
    """PlainLabel and the types in UI built on it, however indirectly."""
    roots = {path.stem: root_type(path) for path in ui.glob("*.qml")}
    found = {"PlainLabel"}
    while True:
        more = {name for name, root in roots.items() if root in found} - found
        if not more:
            return found
        found |= more


def bound(bindings, name_pattern):
    """The expressions bound to each property whose name matches the regex
    NAME_PATTERN, each read on past line ends while brackets are open."""
    for match in re.finditer(r"(?:^|[;\n])\s*(?:" + name_pattern + r")\s*:", bindings):
        depth = 0
        out = []
        for char in bindings[match.end():]:
            if char in ";\n" and depth == 0:
                break
            depth += (char in "([") - (char in ")]")
            out.append(char)
        yield "".join(out).strip()


def binding(bindings, name):
    """The expression bound to NAME; None if NAME is not bound."""
    return next(bound(bindings, re.escape(name)), None)


def is_translated(expression):
    return TRANSLATED.fullmatch(re.sub(r"\s", "", expression)) is not None


def check(ui):
    """(elements examined, rich-text exemptions used, problems) for UI."""
    plain = plain_label_types(ui)
    examined = 0
    exemptions = 0
    problems = []
    for path in sorted(ui.glob("*.qml")):
        source = path.read_text()
        code = blank_comments_and_strings(source)
        formats_bound = 0
        for kind, bindings in declarations(path):
            where = "%s %s" % (path.name, kind)
            text_format = binding(bindings, "textFormat")
            tooltip_format = binding(bindings, "toolTipTextFormat")
            formats_bound += (text_format is not None) + (tooltip_format is not None)
            if kind in plain and path.stem != kind:
                examined += 1
                if text_format is not None:
                    problems.append(where + " overrides PlainLabel's textFormat")
            elif kind in TEXT_TYPES:
                examined += 1
                if text_format != "Text.PlainText":
                    rich_ok = (text_format == "Text.RichText" and path.name == RICH_TEXT_FILE
                               and RICH_TEXT_BINDING in bindings)
                    if rich_ok:
                        exemptions += 1
                    else:
                        problems.append("%s textFormat is %s" % (where, text_format or "unstated"))
            elif text_format is not None:
                problems.append(where + " sets textFormat")
            if kind == "PlasmoidItem":
                examined += 1
                if tooltip_format != "Text.PlainText":
                    problems.append(where + " toolTipTextFormat is not Text.PlainText")
            elif tooltip_format is not None:
                problems.append(where + " sets toolTipTextFormat")
            if kind in SELF_DRAWN_TYPES:
                examined += 1
                for name in SELF_DRAWN_PROPERTIES:
                    text = binding(bindings, name)
                    if text is not None and not is_translated(text):
                        problems.append("%s %s is not translated literals only" % (where, name))
            for pattern in ATTACHED_TEXT:
                for text in bound(bindings, pattern):
                    examined += 1
                    if not is_translated(text):
                        problems.append(where + " attached text is not translated literals only")
        if len(FORMAT_NAMES.findall(code)) != formats_bound:
            problems.append(path.name + " names textFormat outside a binding of it")
        if FORMAT_STRING.search(source):
            problems.append(path.name + " names textFormat in a string")
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
        # The fourth review's forms.
        "data as an argument":   "PlasmaComponents.Button { text: i18n(\"%1\", w.title) }",
        "data added on":         "PlasmaComponents.TabButton { text: i18n(\"x\") + w.title }",
        "check box":             "QQC2.CheckBox { text: w.title }",
        "menu item":             "PlasmaComponents.MenuItem { text: w.title }",
        "action":                "Kirigami.Action { text: w.title }",
        "group box":             "QQC2.GroupBox { title: w.title }",
        "attached tooltip":      "Item { QQC2.ToolTip.text: w.title }",
        "unaliased type":        "Heading { text: w.title }",
        "placeholder":           "PlasmaExtras.PlaceholderMessage { explanation: w.title }",
        "Object.assign":         "Item { Component.onCompleted: Object.assign(x, {textFormat: 4}) }",
        "rich tooltip":          "PlasmoidItem { toolTipTextFormat: Text.RichText }",
        "unstated tooltip":      "PlasmoidItem { toolTipMainText: w.title }",
        "format elsewhere":      "Item { property int f: x.toolTipTextFormat }",
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

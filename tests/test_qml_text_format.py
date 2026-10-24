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
  textFormat to set (buttons, tabs, menu items, actions, a text field's
  placeholder, Kirigami's messages and headers), and the attached
  FormData.label and ToolTip.text,
  are given only constant text: string literals, translated or not, whose
  only arguments are counts (".length");
- textFormat is named nowhere else: not in script (nor any .js file), an
  alias, a Binding, a PropertyChanges or a string;
- no file holds a template literal substitution, which this check cannot
  see into.

Types are matched by name alone, whatever module or alias they come from,
so no file of the widget's may be named like one of those types.
ComboBox models are not checked: the widget's come from its own tables.

Comments and string literals are blanked before checking, so neither can
satisfy or dodge a rule. scripts/render.py checks every text item the
widget declares as it is built, which catches what a source check misses.
"""

import pathlib
import re
import tempfile
import unittest
from typing import ClassVar

UI = pathlib.Path(__file__).resolve().parent.parent / "contents" / "ui"

# Types with a textFormat property that show text.
TEXT_TYPES = {
    "Text",
    "TextEdit",
    "Label",
    "ToolTip",
    "TextArea",
    "Heading",
    "SelectableLabel",
    "LinkButton",
    "UrlButton",
    "DescriptiveLabel",
    "ToolTipArea",
}
# Library types that draw their own text, as AutoText or with no textFormat
# to set, and the properties they draw it from. A TextField's text is what
# is typed, shown by a TextInput, which has no rich text; its placeholder is
# drawn as AutoText.
SELF_DRAWN = {
    **{
        name: ("text",)
        for name in (
            "Button",
            "TabButton",
            "ToolButton",
            "RoundButton",
            "DelayButton",
            "CheckBox",
            "RadioButton",
            "Switch",
            "ItemDelegate",
            "CheckDelegate",
            "RadioDelegate",
            "SwitchDelegate",
            "SwipeDelegate",
            "MenuItem",
            "Action",
            "InlineMessage",
            "ListSectionHeader",
            "Chip",
        )
    },
    "GroupBox": ("title",),
    "PlaceholderMessage": ("text", "explanation"),
    "TextField": ("placeholderText",),
}
# Attached properties drawn as AutoText.
ATTACHED_TEXT = (r"(?:\w+\.)*FormData\.label", r"(?:\w+\.)*ToolTip\.text")
# String literals, and i18n calls on them whose only other arguments are
# counts.
_CALL = r"i18n[cp]*\(S(?:\+S)*(?:,S(?:\+S)*)*(?:,[\w.]+\.length)*\)"
CONSTANT_TEXT = re.compile(rf"(?:{_CALL}|S)(?:\+(?:{_CALL}|S))*")
FORMAT_NAMES = re.compile(r"\b(?:textFormat|toolTipTextFormat)\b")
FORMAT_STRING = re.compile(r"""(["'`])\s*(?:textFormat|toolTipTextFormat)\s*\1""")
# The one element allowed to render RichText: the warning body, which
# poll.py's allowlist has already rebuilt, and nothing else.
RICH_TEXT_FILE = "WarningsTab.qml"
RICH_TEXT = "modelData.html"

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
        for char in bindings[match.end() :]:
            if char in ";\n" and depth == 0:
                break
            depth += (char in "([") - (char in ")]")
            out.append(char)
        yield "".join(out).strip()


def binding(bindings, name):
    """The expression bound to NAME; None if NAME is not bound."""
    return next(bound(bindings, re.escape(name)), None)


def is_constant(expression):
    return CONSTANT_TEXT.fullmatch(re.sub(r"\s", "", expression)) is not None


def check(ui):
    """(elements examined, rich-text exemptions used, problems) for UI."""
    plain = plain_label_types(ui)
    examined = 0
    exemptions = 0
    problems = []
    for path in sorted(ui.glob("*.js")):
        if FORMAT_NAMES.search(path.read_text()):
            problems.append(path.name + " names textFormat")
    for path in sorted(ui.glob("*.qml")):
        source = path.read_text()
        code = blank_comments_and_strings(source)
        formats_bound = 0
        if path.stem in TEXT_TYPES | set(SELF_DRAWN) | {"PlasmoidItem"}:
            problems.append(path.name + " is named like a library type")
        if "${" in source:
            problems.append(path.name + " has a template literal substitution")
        for kind, bindings in declarations(path):
            where = f"{path.name} {kind}"
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
                    rich_ok = (
                        text_format == "Text.RichText"
                        and path.name == RICH_TEXT_FILE
                        and binding(bindings, "text") == RICH_TEXT
                    )
                    if rich_ok:
                        exemptions += 1
                    else:
                        problems.append(f"{where} textFormat is {text_format or 'unstated'}")
            elif text_format is not None:
                problems.append(where + " sets textFormat")
            if kind == "PlasmoidItem":
                examined += 1
                if tooltip_format != "Text.PlainText":
                    problems.append(where + " toolTipTextFormat is not Text.PlainText")
            elif tooltip_format is not None:
                problems.append(where + " sets toolTipTextFormat")
            if kind in SELF_DRAWN:
                examined += 1
                for name in SELF_DRAWN[kind]:
                    text = binding(bindings, name)
                    if text is not None and not is_constant(text):
                        problems.append(f"{where} {name} is not constant text")
            for pattern in ATTACHED_TEXT:
                for text in bound(bindings, pattern):
                    examined += 1
                    if not is_constant(text):
                        problems.append(where + " attached text is not constant text")
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
    rendered as markup, added to a copy of the real UI, must be caught by
    the rule meant for it."""

    # An object added inside an Item in Injected.qml: (QML, the problem it
    # must cause).
    INJECTED: ClassVar[dict[str, tuple[str, str]]] = {
        "inline delegate": (
            "Repeater { delegate: PlasmaComponents.Label { text: w.title } }",
            "textFormat is unstated",
        ),
        "styled PlainLabel": (
            "PlainLabel { textFormat: Text.StyledText; text: w.title }",
            "overrides PlainLabel's textFormat",
        ),
        "AutoText": (
            "Text { textFormat: Text.AutoText; text: w.title }",
            "textFormat is Text.AutoText",
        ),
        "format in a comment": (
            "Text { /* textFormat: Text.PlainText */ text: w.title }",
            "textFormat is unstated",
        ),
        "format in a string": (
            'Text { text: "textFormat: Text.PlainText" + w.title }',
            "textFormat is unstated",
        ),
        "contentItem": (
            "Item { property Item contentItem: Text { text: w.title } }",
            "textFormat is unstated",
        ),
        "bare Label": ("Label { text: w.title }", "textFormat is unstated"),
        "rich text elsewhere": (
            "Text { textFormat: Text.RichText; text: w.title }",
            "textFormat is Text.RichText",
        ),
        "message from data": ("Kirigami.InlineMessage { text: w.title }", "text is not constant"),
        # The second review's forms.
        "descriptive label": (
            "PlasmaExtras.DescriptiveLabel { text: w.title }",
            "textFormat is unstated",
        ),
        "link button": ("Kirigami.LinkButton { text: w.title }", "textFormat is unstated"),
        "tooltip area": ("PlasmaCore.ToolTipArea { mainText: w.title }", "textFormat is unstated"),
        "form label from data": (
            "Item { Kirigami.FormData.label: w.title }",
            "attached text is not constant",
        ),
        "imperative format": (
            "PlainLabel { Component.onCompleted: textFormat = Text.StyledText }",
            "names textFormat outside a binding",
        ),
        "Binding": (
            'Binding { target: x; property: "textFormat"; value: Text.AutoText }',
            "names textFormat in a string",
        ),
        "PropertyChanges": (
            "PropertyChanges { target: x; textFormat: Text.AutoText }",
            "sets textFormat",
        ),
        # The third review's forms.
        "alias property": (
            "Item { property alias f: x.textFormat }",
            "names textFormat outside a binding",
        ),
        "set by name": (
            'Item { Component.onCompleted: x["textFormat"] = 4 }',
            "names textFormat in a string",
        ),
        "section header": ("Kirigami.ListSectionHeader { text: w.title }", "text is not constant"),
        "button with data": ("PlasmaComponents.Button { text: w.title }", "text is not constant"),
        # The fourth review's forms.
        "data as an argument": (
            'PlasmaComponents.Button { text: i18n("%1", w.title) }',
            "text is not constant",
        ),
        "data added on": (
            'PlasmaComponents.TabButton { text: i18n("x") + w.title }',
            "text is not constant",
        ),
        "check box": ("QQC2.CheckBox { text: w.title }", "text is not constant"),
        "menu item": ("PlasmaComponents.MenuItem { text: w.title }", "text is not constant"),
        "action": ("Kirigami.Action { text: w.title }", "text is not constant"),
        "group box": ("QQC2.GroupBox { title: w.title }", "title is not constant"),
        "attached tooltip": (
            "Item { QQC2.ToolTip.text: w.title }",
            "attached text is not constant",
        ),
        "unaliased type": ("Heading { text: w.title }", "textFormat is unstated"),
        "placeholder": (
            "PlasmaExtras.PlaceholderMessage { explanation: w.title }",
            "explanation is not constant",
        ),
        "Object.assign": (
            "Item { Component.onCompleted: Object.assign(x, {textFormat: 4}) }",
            "names textFormat outside a binding",
        ),
        "rich tooltip": (
            "PlasmoidItem { toolTipTextFormat: Text.RichText }",
            "toolTipTextFormat is not Text.PlainText",
        ),
        "unstated tooltip": (
            "PlasmoidItem { toolTipMainText: w.title }",
            "toolTipTextFormat is not Text.PlainText",
        ),
        "format elsewhere": (
            "Item { property int f: x.toolTipTextFormat }",
            "names textFormat outside a binding",
        ),
        # The fifth review's forms.
        "template literal": (
            "Item { Component.onCompleted: `${x.textFormat = 2}` }",
            "template literal substitution",
        ),
        "placeholder text": (
            "QQC2.TextField { placeholderText: w.title }",
            "placeholderText is not constant",
        ),
    }

    # Whole files added to the UI: {file name: (source, the problem it must
    # cause)}.
    INJECTED_FILES: ClassVar[dict[str, tuple[str, str, str]]] = {
        "type built on PlainLabel": (
            "Injected.qml",
            "PlainLabel { textFormat: Text.StyledText }",
            "overrides PlainLabel's textFormat",
        ),
        "PC.Label": (
            "Injected.qml",
            "import org.kde.plasma.components as PC\nItem { PC.Label { text: w.title } }",
            "textFormat is unstated",
        ),
        "QQ.Text": (
            "Injected.qml",
            "import QtQuick as QQ\nQQ.Item { QQ.Text { text: w.title } }",
            "textFormat is unstated",
        ),
        "Basic": (
            "Injected.qml",
            "import QtQuick.Controls.Basic as B\nItem { B.Label { text: w.title } }",
            "textFormat is unstated",
        ),
        "K.FormData": (
            "Injected.qml",
            "import org.kde.kirigami as K\nItem { Item { K.FormData.label: w.title } }",
            "attached text is not constant",
        ),
        "format set in a .js file": (
            "injected.js",
            "function f(x) { x.textFormat = 2 }",
            "injected.js names textFormat",
        ),
        "own type named like a library one": (
            "Heading.qml",
            "PlainLabel {}",
            "Heading.qml is named like a library type",
        ),
    }

    # Edits to the real UI: {name: (file, text, replacement, the problem it
    # must cause)}.
    INJECTED_EDITS: ClassVar[dict[str, tuple[str, str, str, str]]] = {
        "data added to the warning body": (
            "WarningsTab.qml",
            "text: modelData.html",
            "text: modelData.html + modelData.title",
            "textFormat is Text.RichText",
        ),
    }

    def problems(self, files=(), edit=None):
        """check()'s problems for a copy of the real UI with FILES (name,
        source) added and EDIT (file, text, replacement) made."""
        with tempfile.TemporaryDirectory() as tmp:
            ui = pathlib.Path(tmp)
            for path in [*UI.glob("*.qml"), *UI.glob("*.js")]:
                (ui / path.name).write_text(path.read_text())
            for name, source in files:
                (ui / name).write_text(source + "\n")
            if edit:
                name, text, replacement = edit
                source = (ui / name).read_text()
                self.assertEqual(source.count(text), 1, text)
                (ui / name).write_text(source.replace(text, replacement))
            return check(ui)[2]

    def test_typed_text_is_not_flagged(self):
        # What is typed in a TextField is shown as typed.
        self.assertEqual(
            self.problems([("Injected.qml", "Item { QQC2.TextField { text: w.title } }")]), []
        )

    def assertCaught(self, problems, expected):
        self.assertTrue(
            any(expected in problem for problem in problems), f"{expected!r} not among {problems!r}"
        )

    def test_each_injection_is_caught_by_its_rule(self):
        for name, (snippet, expected) in self.INJECTED.items():
            with self.subTest(name):
                problems = self.problems([("Injected.qml", "Item {\n    " + snippet + "\n}")])
                self.assertCaught([p for p in problems if p.startswith("Injected.qml")], expected)
        for name, (file_name, source, expected) in self.INJECTED_FILES.items():
            with self.subTest(name):
                self.assertCaught(self.problems([(file_name, source)]), expected)
        for name, (file_name, text, replacement, expected) in self.INJECTED_EDITS.items():
            with self.subTest(name):
                self.assertCaught(self.problems(edit=(file_name, text, replacement)), expected)


if __name__ == "__main__":
    unittest.main()

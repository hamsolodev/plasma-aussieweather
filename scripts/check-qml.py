#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Compile every QML file in contents/ against the installed Plasma.

    scripts/check-qml.py

qmllint cannot be relied on to fail on QML that does not compile:
redeclaring a FINAL property of Item, for one, is a warning it exits 0
on, and that stopped main.qml loading for nine commits. This compiles
each file with Qt.createComponent, through qmltestrunner, against the
real Plasma 6 QML modules, which CI's Fedora container provides.

Prints how many files it examined, and fails if that is none.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNERS = ["qmltestrunner", "/usr/lib64/qt6/bin/qmltestrunner", "/usr/lib/qt6/bin/qmltestrunner"]

TEST = """import QtQuick
import QtTest

TestCase {
    name: "CompileQml"

    function test_compile_data() {
        return %s
    }

    function test_compile(row) {
        var component = Qt.createComponent(Qt.resolvedUrl(row.file))
        verify(component.status === Component.Ready, component.errorString())
    }
}
"""


def main():
    files = sorted((ROOT / "contents").rglob("*.qml"))
    if not files:
        print("FAIL: no QML files found in contents/", file=sys.stderr)
        return 1
    runner = next((r for r in RUNNERS if shutil.which(r)), None)
    if runner is None:
        print("FAIL: qmltestrunner not found", file=sys.stderr)
        return 1

    rows = [{"tag": f.name, "file": f.as_uri()} for f in files]
    with tempfile.TemporaryDirectory() as tmp:
        test = pathlib.Path(tmp) / "tst_compile.qml"
        test.write_text(TEST % json.dumps(rows))
        # A private config directory: KDE modules write config as they load,
        # and an unwritable one makes KConfig pop up a dialog.
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
                   XDG_CONFIG_HOME=str(pathlib.Path(tmp) / "config"))
        result = subprocess.run([runner, "-input", str(test)], env=env, check=False,
                                capture_output=True, text=True, timeout=300)
    print(result.stdout + result.stderr)
    passed = sum(line.startswith("PASS   : ") and "::test_compile(" in line
                 for line in result.stdout.splitlines())
    if result.returncode != 0 or passed != len(files):
        print(f"FAIL: {passed} of {len(files)} QML files compiled", file=sys.stderr)
        return 1
    print(f"OK: {len(files)} QML files compiled")
    return 0


if __name__ == "__main__":
    sys.exit(main())

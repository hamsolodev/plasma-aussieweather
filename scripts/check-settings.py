#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check the settings page's places editor, offscreen, as a user drives it.

    scripts/check-settings.py

Each case opens the real ConfigPage.qml from a config, as Plasma's dialog
does, acts on it (typing with real key events, clicking the real buttons),
and checks what the page would save and what it shows. Prints how many
checks ran, and fails if any failed, if QML logged a warning, or if none
ran.

Needs KDE Plasma 6's QML modules (with KCMUtils) and PySide6 built against
the same Qt, as scripts/render.py does. CI runs it in a Fedora container.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def entry(search, radar):
    """A saved place, as places.js writes it (JSON.stringify's spacing)."""
    return json.dumps({"search": search, "radar": radar}, separators=(",", ":"))


SEAFORD = entry("Seaford VIC", "IDR023")
PERTH = entry("Perth WA", "IDR703")
# Logged by the offscreen setup itself, not by the page.
EXPECTED_MESSAGES = ("Could not find any platform plugin", "fallback to QtQuick software backend")


def run(config_home):
    os.environ.update(
        {
            "XDG_CONFIG_HOME": config_home,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QPA_PLATFORMTHEME": "kde",
            "QT_QUICK_BACKEND": "software",
        }
    )
    from PySide6.QtCore import (
        Q_ARG,
        Q_RETURN_ARG,
        QMetaObject,
        QTimer,
        QUrl,
        qInstallMessageHandler,
    )
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401 (wraps the window as one)
    from PySide6.QtTest import QTest

    messages = []

    def on_message(kind, context, message):
        if not any(expected in message for expected in EXPECTED_MESSAGES):
            messages.append(message)

    qInstallMessageHandler(on_message)
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    i18n_component = QQmlComponent(
        engine, QUrl.fromLocalFile(str(ROOT / "scripts" / "render-i18n.qml"))
    )
    i18n = i18n_component.create()
    QQmlEngine.setObjectOwnership(i18n, QQmlEngine.ObjectOwnership.CppOwnership)
    engine.rootContext().setContextObject(i18n)
    engine.load(str(ROOT / "scripts" / "check-settings.qml"))
    if not engine.rootObjects():
        print("FAIL: check-settings.qml did not load", file=sys.stderr)
        return 1
    window = engine.rootObjects()[0]

    def settle(seconds=0.2):
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(app.quit)
        timer.start(int(seconds * 1000))
        app.exec()

    def call(name, *args):
        return QMetaObject.invokeMethod(
            window, name, Q_RETURN_ARG("QVariant"), *[Q_ARG("QVariant", a) for a in args]
        )

    def open_page(places, location, radar="IDR023"):
        if not call("open", places, location, radar):
            raise RuntimeError("the settings page did not open")
        settle()

    def state():
        return json.loads(call("state"))

    def type_into(row, text):
        call("focusField", row)
        for char in text:  # keyClicks takes only widgets
            QTest.keyClick(window, char)
        settle()

    checks = 0
    failures = []

    def check(what, actual, expected):
        nonlocal checks
        checks += 1
        if actual != expected:
            failures.append(f"{what}: {actual!r}, not {expected!r}")

    # A config from before saved places: one place, shown, and nothing saved
    # by opening (Plasma would count the config as changed).
    open_page([], "Seaford VIC")
    s = state()
    check("old config, shown", s["shown"], 0)
    check("old config, saved on opening", s["places"], [])
    check("old config, its button", s["buttons"], [[True, True]])

    # A blank place cannot be the one shown.
    call("addPlace")
    settle()
    check("a new blank place's button", state()["buttons"][1], [False, False])

    # Typing a second place leaves the first shown, and saves both.
    type_into(1, "Perth WA")
    s = state()
    check("second place typed, shown", s["shown"], 0)
    check("second place typed, saved", s["places"], [SEAFORD, entry("Perth WA", "IDR022")])
    check("second place typed, its button", s["buttons"][1], [True, False])

    # Marking it shows it, with its radar.
    call("clickShown", 1)
    settle()
    s = state()
    check("second place marked, location", s["locationSearch"], "Perth WA")
    check("second place marked, radar", s["radarStation"], "IDR022")

    # Removing the place shown shows the other.
    call("removePlace", 1)
    settle()
    s = state()
    check("shown place removed, shown", s["shown"], 0)
    check("shown place removed, location", s["locationSearch"], "Seaford VIC")
    check("shown place removed, saved", s["places"], [SEAFORD])

    # No location set: no place shown, and none checked, until one is typed;
    # the first place typed is then shown.
    open_page([], "")
    s = state()
    check("no location, shown", s["shown"], -1)
    check("no location, buttons", s["buttons"], [[False, False]])
    type_into(0, "Perth WA")
    s = state()
    check("first place typed, shown", s["shown"], 0)
    check("first place typed, location", s["locationSearch"], "Perth WA")

    # Saved places with none shown (the place shown was cleared): none is
    # checked, and marking one shows it.
    open_page([SEAFORD, PERTH], "", "IDR022")
    s = state()
    check("none shown, shown", s["shown"], -1)
    check("none shown, buttons", s["buttons"], [[True, False], [True, False]])
    call("clickShown", 1)
    settle()
    s = state()
    check("one marked, location", s["locationSearch"], "Perth WA")
    check("one marked, radar", s["radarStation"], "IDR703")
    check("one marked, buttons", s["buttons"], [[True, False], [True, True]])

    for failure in failures:
        print("FAIL: " + failure, file=sys.stderr)
    for message in messages:
        print("QML: " + message, file=sys.stderr)
    if not checks:
        print("FAIL: no checks ran", file=sys.stderr)
        return 1
    if failures or messages:
        print(
            f"FAIL: {len(failures)} of {checks} checks failed, {len(messages)} QML messages",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {checks} settings page checks")
    return 0


def main():
    with tempfile.TemporaryDirectory(prefix="aussieweather-settings-") as config_home:
        shutil.copy(
            "/usr/share/color-schemes/BreezeLight.colors", pathlib.Path(config_home) / "kdeglobals"
        )
        return run(config_home)


if __name__ == "__main__":
    sys.exit(main())

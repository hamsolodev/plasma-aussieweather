# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Load the widget's fetch scripts (contents/code/*.py) as modules."""

import importlib.util
import pathlib

CODE = pathlib.Path(__file__).resolve().parent.parent / "contents" / "code"


def load(name):
    spec = importlib.util.spec_from_file_location(name, CODE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeApi:
    """Stands in for poll.make_get: answers API paths from a dict.

    A value that is an exception instance is raised instead of returned.
    Every path asked for is recorded in .requested.
    """

    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def __call__(self, path):
        self.requested.append(path)
        if path not in self.responses:
            raise AssertionError("unexpected API request: " + path)
        value = self.responses[path]
        if isinstance(value, Exception):
            raise value
        return value

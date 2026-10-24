# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Load the widget's fetch scripts (contents/code/*.py) as modules.

They are run as scripts, from a directory that is not a package, so the
tests load them by path.
"""

import importlib.util
import pathlib

CODE = pathlib.Path(__file__).resolve().parent.parent / "contents" / "code"


def load(name):
    spec = importlib.util.spec_from_file_location(name, CODE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    conftest.py
# Description: Shared seam for the tests in tests/. Puts the bundle's
#              "Server Plugin" folder on sys.path and imports the bundle's own
#              test_plugin.py, which installs the ONE indigo stand-in this
#              suite uses (a MagicMock with real kStateImageSel names), so
#              plugin.py can be imported here with no Indigo server. Does not
#              define a second stub.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0

import os
import sys

REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_PLUGIN = os.path.join(REPO_ROOT, "UniversalZWaveSensor.indigoPlugin",
                             "Contents", "Server Plugin")
if SERVER_PLUGIN not in sys.path:
    sys.path.insert(0, SERVER_PLUGIN)

import test_plugin  # noqa: E402,F401  (installs sys.modules["indigo"])

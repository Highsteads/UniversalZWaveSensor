#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_xml_callbacks_and_changelog.py
# Description: Generic checks this repo did not have yet:
#                - every <CallbackMethod> and every <List method="..."> named in
#                  the XML exists on Plugin (a missing one only fails when the
#                  user opens that dialog or menu)
#                - every state plugin.py writes by name is declared on at
#                  least one device type in Devices.xml
#                - docs/changelog.md's newest entry is the version Info.plist
#                  ships
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0

import ast
import glob
import os
import plistlib
import re
import xml.etree.ElementTree as ET

import plugin as plugin_module
from conftest import REPO_ROOT, SERVER_PLUGIN

NATIVE_STATES = {"onOffState"}       # supplied by Indigo for relay / sensor types


def _xml_root(name):
    return ET.parse(os.path.join(SERVER_PLUGIN, name)).getroot()


def test_every_xml_callback_exists_on_the_plugin():
    named = []
    for path in sorted(glob.glob(os.path.join(SERVER_PLUGIN, "*.xml"))):
        root = ET.parse(path).getroot()
        for el in root.iter("CallbackMethod"):
            named.append((os.path.basename(path), (el.text or "").strip()))
        for el in root.iter("List"):
            if el.get("method"):
                named.append((os.path.basename(path), el.get("method")))
    assert len(named) >= 6, "expected the menu callbacks and the device pickers"
    missing = [f"{f}: {m}" for f, m in named
               if not callable(getattr(plugin_module.Plugin, m, None))]
    assert not missing, f"XML names methods plugin.py does not define: {missing}"


def test_every_state_written_by_name_is_declared_somewhere():
    with open(os.path.join(SERVER_PLUGIN, "plugin.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    written = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("updateStateOnServer", "_safe_update")):
            args = node.args[1:] if node.func.attr == "_safe_update" else node.args
            if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                written.add(args[0].value)
    declared = {s.get("id") for s in _xml_root("Devices.xml").iter("State")}
    assert {"lastUpdate", "deviceOnline", "displayStatus"} <= written
    undeclared = written - declared - NATIVE_STATES
    assert not undeclared, f"written but declared on no device type: {sorted(undeclared)}"


def test_docs_changelog_newest_entry_is_this_version():
    plist = glob.glob(os.path.join(REPO_ROOT, "*.indigoPlugin", "Contents", "Info.plist"))[0]
    with open(plist, "rb") as fh:
        version = plistlib.load(fh)["PluginVersion"]
    with open(os.path.join(REPO_ROOT, "docs", "changelog.md"), encoding="utf-8") as fh:
        entries = re.findall(r"^##\s+v?(\d+(?:\.\d+)+)\b", fh.read(), re.M)
    assert entries, "docs/changelog.md has no '## <version>' entries"
    assert entries[0] == version, f"newest changelog entry {entries[0]}, Info.plist {version}"

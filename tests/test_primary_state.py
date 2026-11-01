#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_primary_state.py
# Description: v5.18 - which reports may set a device's primary on/off state
#              (onOffState). Every kind of report the plugin decodes is sent,
#              through the real _route_zwave_report, to every device type, and
#              the test checks the primary state changed exactly where that
#              report is the device's job:
#                motion  -> Motion          contact/barrier -> Contact
#                lock    -> Lock            switch/dimmer   -> Plug, Energy
#                scene   -> Scene           alarms, mains power, tamper -> none
#              plus Generic for everything. Basic and untyped binary reports
#              set every device, because older sensors rely on them.
#              Before 5.18 every report set every device's primary state, so a
#              door contact sharing a node with a siren, a lock, a dimmer or a
#              mains monitor was switched by those reports.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0

import pytest

from test_plugin import MockDevice, make_plugin

ALL_TYPES = ("motion", "contact", "temperature", "humidity", "luminance", "energy",
             "plug", "battery", "lock", "scene", "generic")


def _notif(ntype, event):
    return [0x71, 0x05, 0, 0, 0, 0xFF, ntype, event, 0x00]


# (description, frame, device types whose primary state it may set)
REPORTS = [
    ("HS motion",            _notif(0x07, 0x08),         {"motion", "generic"}),
    ("door open",            _notif(0x06, 0x16),         {"contact", "generic"}),
    ("lock (notification)",  _notif(0x06, 0x01),         {"lock", "generic"}),
    ("water leak",           _notif(0x05, 0x02),         {"generic"}),
    ("smoke",                _notif(0x01, 0x02),         {"generic"}),
    ("CO",                   _notif(0x02, 0x01),         {"generic"}),
    ("gas",                  _notif(0x12, 0x01),         {"generic"}),
    ("siren",                _notif(0x0E, 0x01),         {"generic"}),
    ("mains restored",       _notif(0x08, 0x03),         {"generic"}),
    ("binary motion",        [0x30, 0x03, 0xFF, 0x0C],   {"motion", "generic"}),
    ("binary door",          [0x30, 0x03, 0xFF, 0x0A],   {"contact", "generic"}),
    ("binary smoke",         [0x30, 0x03, 0xFF, 0x02],   {"generic"}),
    ("binary water",         [0x30, 0x03, 0xFF, 0x06],   {"generic"}),
    ("binary tamper",        [0x30, 0x03, 0xFF, 0x08],   {"generic"}),
    ("switch on",            [0x25, 0x03, 0xFF],         {"plug", "energy", "generic"}),
    ("dimmer 50%",           [0x26, 0x03, 0x32],         {"plug", "energy", "generic"}),
    ("barrier open",         [0x66, 0x03, 0xFF],         {"contact", "generic"}),
    ("central scene",        [0x5B, 0x03, 0x01, 0x00, 0x01], {"scene", "generic"}),
    ("scene activation",     [0x2B, 0x01, 0x01],         {"scene", "generic"}),
    ("door lock",            [0x62, 0x03, 0xFF],         {"lock", "generic"}),
    # Untyped: "the sensor's main thing" - every device, as before.
    ("basic set",            [0x20, 0x01, 0xFF],         set(ALL_TYPES)),
    ("binary untyped (v1)",  [0x30, 0x03, 0xFF],         set(ALL_TYPES)),
    ("binary general",       [0x30, 0x03, 0xFF, 0x01],   set(ALL_TYPES)),
]


@pytest.mark.parametrize("desc, frame, allowed", REPORTS, ids=[r[0] for r in REPORTS])
@pytest.mark.parametrize("dev_type", ALL_TYPES)
def test_primary_state_changes_only_where_the_report_is_the_devices_job(
        desc, frame, allowed, dev_type):
    p = make_plugin()
    dev = MockDevice(1, "Dev", address="12",
                     plugin_props={"sensorType": dev_type, "endpointId": ""})
    p._route_zwave_report(dev, 12, frame[0], frame[1], frame, "")
    wrote = "onOffState" in dev.state_writes
    if dev_type in allowed:
        assert wrote, f"{desc} should set a {dev_type} device's primary state"
        assert dev.state_writes["onOffState"]["value"] is True
    else:
        assert not wrote, f"{desc} changed a {dev_type} device's primary state"


def test_a_door_contact_on_a_node_with_a_siren_stays_open():
    """The kind of mix that went wrong: one node, a door contact device, and a
    siren silencing on the same node."""
    p = make_plugin()
    door = MockDevice(1, "Back Door", address="12",
                      plugin_props={"sensorType": "contact", "endpointId": ""})
    for frame in (_notif(0x06, 0x16), _notif(0x0E, 0x01), _notif(0x0E, 0x00)):
        p._route_zwave_report(door, 12, frame[0], frame[1], frame, "")
    assert door.states.get("onOffState") is True
    assert door.states.get("contact") is True


def test_the_report_own_state_still_updates_on_every_device_that_has_it():
    """Only the PRIMARY state is restricted: a lock device still records a
    door contact on its node in its own contact state, if it has one."""
    p = make_plugin()
    lock = MockDevice(1, "Front Lock", address="12",
                      plugin_props={"sensorType": "lock", "endpointId": ""})
    frame = _notif(0x06, 0x16)
    p._route_zwave_report(lock, 12, frame[0], frame[1], frame, "")
    assert lock.states.get("contact") is True
    assert "onOffState" not in lock.state_writes

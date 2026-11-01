#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_zwave_code_tables.py
# Description: The plugin's Z-Wave code tables against the Z-Wave standard, and
#              what the decoders do with real-shaped reports.
#
#              Reference for the expected values: the zwave-js project's
#              definitions, fetched 01-11-2026 —
#                packages/cc/src/lib/_Types.ts          (enum BinarySensorType)
#                packages/core/src/registries/Sensors.ts (multilevel sensor types)
#                packages/core/src/registries/Notifications.ts
#              Each mismatch that is a real fault is xfail(strict=True) with the
#              fault in the reason, so the suite stays green today and goes red
#              (XPASS) the moment the table is corrected, prompting removal of
#              the marker.
# Author:      CliveS & Claude Opus 5.5
# Date:        01-11-2026
# Version:     1.0

import pytest

import plugin as P
from test_plugin import MockDevice, make_plugin

# ------------------------------------------------------------ the standard

# Sensor Binary CC sensor types (zwave-js BinarySensorType).
BINARY_STANDARD = {0x01: "General purpose", 0x02: "Smoke", 0x03: "CO", 0x04: "CO2",
                   0x05: "Heat", 0x06: "Water", 0x07: "Freeze", 0x08: "Tamper",
                   0x09: "Aux", 0x0A: "Door/Window", 0x0B: "Tilt", 0x0C: "Motion",
                   0x0D: "Glass break"}

# Sensor Multilevel CC sensor types (zwave-js Sensors.ts).
MULTILEVEL_STANDARD = {0x01: "Air temperature", 0x03: "Illuminance", 0x04: "Power",
                       0x05: "Humidity", 0x06: "Velocity", 0x08: "Atmospheric pressure",
                       0x09: "Barometric pressure", 0x0B: "Dew point", 0x0E: "Weight",
                       0x0F: "Voltage", 0x10: "Current", 0x11: "CO2 level",
                       0x12: "Air flow", 0x13: "Tank capacity", 0x15: "Angle position",
                       0x19: "Seismic intensity", 0x1B: "Ultraviolet",
                       0x1C: "Electrical resistivity", 0x1F: "Moisture"}

BINARY_BUG = ("BUG: BINARY_SENSOR_TYPES does not follow the Z-Wave Sensor Binary "
              "types: 0x04 is CO2 (plugin: waterLeak), 0x06 is Water (plugin: "
              "tamper), 0x08 is Tamper (plugin: motion), 0x09 Aux and 0x0B Tilt "
              "(plugin: motion). A leak reported this way sets 'tamper', not "
              "'waterLeak'; a cover-removed tamper sets 'motion'.")

MULTILEVEL_BUG = ("BUG: SENSOR_TYPES is right up to 0x09 but wrong from 0x0B: 0x0F is "
                  "Voltage (plugin: co2Level), 0x10 Current (plugin: watts), 0x11 CO2 "
                  "(plugin: uvIndex), 0x12 Air flow (plugin: voltage), 0x13 Tank "
                  "capacity (plugin: current), 0x1B Ultraviolet (plugin: noise), "
                  "0x1F Moisture (plugin: pm25), and others.")


# ------------------------------------------------------------ what is right

@pytest.mark.parametrize("code, key", [(0x02, "smoke"), (0x03, "coAlarm"),
                                       (0x0A, "contact"), (0x0C, "motion")])
def test_binary_types_the_plugin_has_right(code, key):
    assert P.BINARY_SENSOR_TYPES[code] == key


@pytest.mark.parametrize("code, key", [(0x01, "temperature"), (0x03, "luminance"),
                                       (0x04, "watts"), (0x05, "humidity")])
def test_multilevel_types_the_plugin_has_right(code, key):
    assert P.SENSOR_TYPES[code][0] == key


@pytest.mark.parametrize("name, code", [
    ("NOTIF_SMOKE", 0x01), ("NOTIF_CO", 0x02), ("NOTIF_WATER", 0x05),
    ("NOTIF_ACCESS_CONTROL", 0x06), ("NOTIF_HOME_SECURITY", 0x07),
    ("HS_INTRUSION", 0x01), ("HS_INTRUSION_NL", 0x02), ("HS_TAMPER", 0x03),
    ("HS_GLASS_BREAK", 0x05), ("HS_GLASS_BREAK_NL", 0x06),
    ("HS_MOTION_DETECTED", 0x07), ("HS_MOTION_DETECTED_NL", 0x08),
    ("HS_TAMPER_ALT", 0x09), ("AC_DOOR_OPEN", 0x16), ("AC_DOOR_CLOSED", 0x17),
])
def test_notification_codes_match_the_standard(name, code):
    assert getattr(P, name) == code


# ------------------------------------------------------------ the binary table

@pytest.mark.xfail(strict=True, reason=BINARY_BUG)
def test_binary_table_follows_the_standard():
    wrong = {code: P.BINARY_SENSOR_TYPES[code] for code in (0x04, 0x06, 0x08, 0x09, 0x0B)
             if code in P.BINARY_SENSOR_TYPES}
    expect = {0x06: "waterLeak", 0x08: "tamper"}
    assert {k: v for k, v in wrong.items() if k in expect} == expect
    assert P.BINARY_SENSOR_TYPES.get(0x04) != "waterLeak"
    assert P.BINARY_SENSOR_TYPES.get(0x09) != "motion"
    assert P.BINARY_SENSOR_TYPES.get(0x0B) != "motion"


@pytest.mark.xfail(strict=True, reason=BINARY_BUG)
def test_a_binary_water_report_sets_water_leak():
    p = make_plugin()
    dev = MockDevice(1, "Kitchen Leak", plugin_props={"sensorType": "generic"})
    p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x06])      # type 0x06 = Water
    assert dev.states.get("waterLeak") is True


@pytest.mark.xfail(strict=True, reason=BINARY_BUG)
def test_a_binary_tamper_report_is_not_motion():
    p = make_plugin()
    dev = MockDevice(1, "Hall PIR", plugin_props={"sensorType": "generic"})
    p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x08])      # type 0x08 = Tamper
    assert dev.states.get("motion") is not True
    assert dev.states.get("tamper") is True


# ------------------------------------------------------------ the multilevel table

@pytest.mark.xfail(strict=True, reason=MULTILEVEL_BUG)
def test_multilevel_table_follows_the_standard():
    expect = {0x0F: "voltage", 0x10: "current", 0x11: "co2Level"}
    assert {k: P.SENSOR_TYPES[k][0] for k in expect} == expect


@pytest.mark.xfail(strict=True, reason=MULTILEVEL_BUG)
def test_a_current_report_does_not_land_in_watts():
    p = make_plugin()
    dev = MockDevice(1, "Kettle Plug", plugin_props={"sensorType": "energy"})
    # 0x10 Current, precision 1, scale 0 (A), size 2: 0x0005 -> 0.5 A
    p._handle_multilevel(dev, [0x31, 0x05, 0x10, 0x22, 0x00, 0x05])
    assert "watts" not in dev.state_writes, "0.5 A was written as 0.5 W"


# ------------------------------------------------------------ idle events

IDLE_BUG = ("BUG: a Home Security 'idle' notification (event 0x00) names the event "
            "that ended in its first event parameter, but _handle_notification clears "
            "motion AND tamper on every idle, and writes onOffState=False whatever the "
            "device type. Motion ending clears a tamper that is still active.")


@pytest.mark.xfail(strict=True, reason=IDLE_BUG)
def test_motion_ending_does_not_clear_an_active_tamper():
    p = make_plugin()
    dev = MockDevice(1, "Hall PIR", plugin_props={"sensorType": "motion"})
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x03, 0x00])  # cover off
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x08, 0x00])  # motion
    # idle, event parameter 0x08: motion has ended
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x00, 0x01, 0x08])
    assert dev.states.get("motion") is False
    assert dev.states.get("tamper") is True, "the cover is still off"


@pytest.mark.xfail(strict=True, reason=IDLE_BUG)
def test_a_tamper_clearing_does_not_close_a_door_contact():
    p = make_plugin()
    dev = MockDevice(1, "Back Door", plugin_props={"sensorType": "contact"})
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x06, 0x16, 0x00])  # door open
    # Home Security idle, event parameter 0x03: the cover went back on
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x00, 0x01, 0x03])
    assert dev.states.get("contact") is True
    assert dev.states.get("onOffState") is True, "the door's primary state went to closed"


def test_a_plain_idle_still_clears_motion():
    """An idle with no event parameter (older devices) must keep clearing motion."""
    p = make_plugin()
    dev = MockDevice(1, "Hall PIR", plugin_props={"sensorType": "motion"})
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x08, 0x00])
    p._handle_notification(dev, [0x71, 0x05, 0, 0, 0, 0xFF, 0x07, 0x00, 0x00])
    assert dev.states.get("motion") is False

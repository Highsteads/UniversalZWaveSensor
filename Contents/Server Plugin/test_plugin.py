#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_plugin.py
# Description: Mock test suite for Universal Z-Wave Sensor plugin v3.2
#              Covers all raw Z-Wave parsers, validateDeviceConfigUi (native
#              device picker), subscribeToIncoming(), NOTIFICATION byte order
#              auto-detection, multi-channel routing, stale detection,
#              temperature units, and wake-up interval handling.
# Author:      CliveS & Claude Sonnet 4.6
# Date:        22-03-2026
# Version:     3.2
#
# Run from the Server Plugin directory:
#   python3 test_plugin.py -v

import os
import sys
import struct
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock


# ==============================================================================
# Mock indigo module
# Must be installed into sys.modules BEFORE plugin.py is imported.
# ==============================================================================

class _StateImageSel:
    """Named constants matching indigo.kStateImageSel values used by the plugin."""
    TemperatureSensor   = "TemperatureSensor"
    HumiditySensor      = "HumiditySensor"
    LightSensor         = "LightSensor"
    LightSensorOn       = "LightSensorOn"
    MotionSensor        = "MotionSensor"
    MotionSensorTripped = "MotionSensorTripped"
    SensorOn            = "SensorOn"
    SensorOff           = "SensorOff"
    SensorTripped       = "SensorTripped"
    PowerOn             = "PowerOn"
    PowerOff            = "PowerOff"


class MockDevice:
    """
    Minimal Indigo device substitute.
    Captures all updateStateOnServer / updateStateImageOnServer calls
    so tests can assert on the values written.
    """
    def __init__(self, dev_id, name, address="", plugin_id="",
                 states=None, plugin_props=None, on_state=None):
        self.id          = dev_id
        self.name        = name
        self.address     = str(address)
        self.pluginId    = plugin_id
        self.states      = dict(states or {})
        self.pluginProps = dict(plugin_props or {})
        self._on_state   = on_state

        # Capture all writes during the test
        self.state_writes = {}          # key -> {"value": v, "uiValue": u}
        self.image_writes = []          # list of image selector strings

    def __repr__(self):
        return f"MockDevice(id={self.id}, name={self.name!r})"

    def updateStateOnServer(self, key, value=None, uiValue=None):
        self.states[key]       = value
        self.state_writes[key] = {"value": value, "uiValue": uiValue}

    def updateStateImageOnServer(self, sel):
        self.image_writes.append(sel)

    def stateListOrDisplayStateIdChanged(self):
        pass

    @property
    def onState(self):
        if self._on_state is None:
            raise AttributeError(f"'{self.name}' has no onState")
        return self._on_state


class MockDevicesDict(dict):
    """
    Supports indigo.devices[id] lookups, indigo.devices.iter('self'),
    and plain iteration (for dev in indigo.devices) — all return device objects.
    """
    def iter(self, filter_str=""):
        return list(self.values())

    def __iter__(self):
        return iter(self.values())


# Build and register the mock indigo module
_indigo              = MagicMock()
_indigo.kStateImageSel = _StateImageSel()
_indigo.PluginBase   = object           # Plugin inherits from this
sys.modules["indigo"] = _indigo

# Import plugin.py from the same directory as this test file
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import plugin as _plugin_mod            # noqa: E402  (after sys.modules patch)


# ==============================================================================
# Helper: create a Plugin instance without triggering the Indigo lifecycle
# ==============================================================================

def make_plugin(debug=False, temp_unit="degC"):
    p = _plugin_mod.Plugin.__new__(_plugin_mod.Plugin)
    p.debug           = debug
    p.log_unknown     = True
    p.temp_unit       = temp_unit
    p.stale_enabled   = True
    p.stale_hours     = 24
    p.pluginId        = "com.clives.universal-zwave-sensor"
    p.node_to_device  = {}
    p.stale_device_ids = set()
    p.logger          = MagicMock()
    return p


# ==============================================================================
# Tests: validateDeviceConfigUi — native device picker and endpoint validation
# ==============================================================================

class TestValidateDeviceConfigUi(unittest.TestCase):

    def setUp(self):
        self.p        = make_plugin()
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict
        _indigo.Dict    = dict

    def _native(self, dev_id, name, node_str):
        dev = MockDevice(dev_id, name, address=node_str,
                         plugin_id="com.perceptiveautomation.indigoplugin.zwave")
        dev.ownerProps = {"address": node_str}
        self.dev_dict[dev_id] = dev
        return dev

    def _validate(self, source_dev_id, endpoint_str=""):
        values_dict = {
            "sourceDeviceId": str(source_dev_id),
            "nodeId":         "",
            "endpointId":     endpoint_str,
        }
        return self.p.validateDeviceConfigUi(values_dict, "zwaveSensor", 0)

    def test_valid_device_selected_passes(self):
        """Selecting a valid native device populates nodeId and address."""
        self._native(5, "Front Door Sensor", "156")
        ok, values, errors = self._validate(5)
        self.assertTrue(ok)
        self.assertEqual(values["nodeId"],  "156")
        self.assertEqual(values["address"], "156")
        self.assertNotIn("sourceDeviceId", errors)

    def test_no_device_selected_fails(self):
        """Value 'none' (nothing selected) is rejected."""
        ok, _, errors = self._validate("none")
        self.assertFalse(ok)
        self.assertIn("sourceDeviceId", errors)

    def test_blank_source_fails(self):
        """Blank sourceDeviceId is rejected."""
        ok, _, errors = self._validate("")
        self.assertFalse(ok)
        self.assertIn("sourceDeviceId", errors)

    def test_device_with_non_numeric_address_fails(self):
        """Native device with non-numeric address produces a clear error."""
        dev = MockDevice(9, "Bad Device", address="not-a-node",
                         plugin_id="com.perceptiveautomation.indigoplugin.zwave")
        dev.ownerProps = {"address": "not-a-node"}
        self.dev_dict[9] = dev
        ok, _, errors = self._validate(9)
        self.assertFalse(ok)
        self.assertIn("sourceDeviceId", errors)

    def test_logs_info_on_success(self):
        """Successful validation logs the resolved node ID."""
        self._native(5, "Door Sensor", "156")
        self._validate(5)
        self.p.logger.info.assert_called()

    def test_valid_endpoint_passes(self):
        self._native(5, "Door Sensor", "42")
        ok, _, errors = self._validate(5, endpoint_str="2")
        self.assertTrue(ok)
        self.assertNotIn("endpointId", errors)

    def test_invalid_endpoint_rejected(self):
        self._native(5, "Door Sensor", "42")
        ok, _, errors = self._validate(5, endpoint_str="abc")
        self.assertFalse(ok)
        self.assertIn("endpointId", errors)

    def test_blank_endpoint_passes(self):
        self._native(5, "Door Sensor", "42")
        ok, _, errors = self._validate(5, endpoint_str="")
        self.assertTrue(ok)
        self.assertNotIn("endpointId", errors)


# ==============================================================================
# Tests: Multi-channel encapsulation routing
# ==============================================================================

class TestMultiChannelRouting(unittest.TestCase):
    """CC 0x60, CMD 0x0D — unwrap inner frame, optionally filter by endpoint."""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self, endpoint_id=""):
        return MockDevice(1, "Test", address="223",
                          plugin_props={"sensorType": "temperature",
                                        "endpointId": endpoint_id})

    def _mc_wrap(self, src_ep, dst_ep, inner_bytes):
        """Build a MULTI_CHANNEL_CMD_ENCAP frame."""
        return [0x60, 0x0D, src_ep, dst_ep] + list(inner_bytes)

    def test_mc_encap_unwraps_and_routes(self):
        """Wrapped temperature report is unwrapped and processed correctly."""
        # 21.5 degC inner frame
        pss = (1 << 5) | (0 << 3) | 2   # precision=1, scale=0, size=2
        inner = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 215))
        raw = self._mc_wrap(1, 2, inner)
        dev = self._dev(endpoint_id="")   # accept all
        self.p._route_zwave_report(dev, 223, raw[0], raw[1], raw, "")
        self.assertIn("temperature", dev.state_writes)
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 21.5)

    def test_mc_endpoint_filter_match_processes(self):
        """Report with dst_ep matching configured endpoint is processed."""
        pss = (1 << 5) | (0 << 3) | 2
        inner = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 215))
        raw = self._mc_wrap(0, 2, inner)
        dev = self._dev(endpoint_id="2")
        self.p._route_zwave_report(dev, 223, raw[0], raw[1], raw, "")
        self.assertIn("temperature", dev.state_writes)

    def test_mc_endpoint_filter_mismatch_skips(self):
        """Report with dst_ep NOT matching configured endpoint is silently skipped."""
        pss = (1 << 5) | (0 << 3) | 2
        inner = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 215))
        raw = self._mc_wrap(0, 3, inner)   # dst_ep=3
        dev = self._dev(endpoint_id="2")   # want ep 2
        self.p._route_zwave_report(dev, 223, raw[0], raw[1], raw, "")
        self.assertNotIn("temperature", dev.state_writes)

    def test_mc_endpoint_zero_accepts_all(self):
        """endpointId=0 means accept all endpoints."""
        pss = (1 << 5) | (0 << 3) | 2
        inner = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 215))
        raw = self._mc_wrap(0, 5, inner)   # any dst_ep
        dev = self._dev(endpoint_id="0")
        self.p._route_zwave_report(dev, 223, raw[0], raw[1], raw, "")
        self.assertIn("temperature", dev.state_writes)

    def test_mc_too_short_silently_dropped(self):
        """MC frame with fewer than 6 bytes is dropped without crashing."""
        raw = [0x60, 0x0D, 0x01]   # truncated
        dev = self._dev()
        self.p._route_zwave_report(dev, 223, raw[0], raw[1], raw, "")
        self.assertEqual(dev.state_writes, {})


# ==============================================================================
# Tests: Temperature unit conversion
# ==============================================================================

class TestTemperatureUnit(unittest.TestCase):
    """Verify degC<->degF conversion in _handle_multilevel."""

    def _dev(self):
        return MockDevice(1, "Temp Test", address="50",
                          plugin_props={"sensorType": "temperature"})

    def _raw_temp(self, raw_int, precision, scale):
        pss = (precision << 5) | (scale << 3) | 2   # size=2
        return [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", raw_int))

    def test_degC_reported_pref_degC_no_conversion(self):
        """21.5 degC reported, pref=degC -> stored as 21.5 degC."""
        p   = make_plugin(temp_unit="degC")
        dev = self._dev()
        p._handle_multilevel(dev, self._raw_temp(215, 1, 0))
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 21.5, places=1)
        self.assertIn("degC", dev.state_writes["temperature"]["uiValue"])

    def test_degF_reported_pref_degF_no_conversion(self):
        """70 degF reported, pref=degF -> stored as 70.0 degF."""
        p   = make_plugin(temp_unit="degF")
        dev = self._dev()
        p._handle_multilevel(dev, self._raw_temp(70, 0, 1))   # scale=1 = degF
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 70.0, places=1)
        self.assertIn("degF", dev.state_writes["temperature"]["uiValue"])

    def test_degC_reported_pref_degF_converts(self):
        """21.5 degC reported, pref=degF -> stored as 70.7 degF."""
        p   = make_plugin(temp_unit="degF")
        dev = self._dev()
        p._handle_multilevel(dev, self._raw_temp(215, 1, 0))
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 70.7, places=1)
        self.assertIn("degF", dev.state_writes["temperature"]["uiValue"])

    def test_degF_reported_pref_degC_converts(self):
        """70 degF reported, pref=degC -> stored as approx 21.1 degC."""
        p   = make_plugin(temp_unit="degC")
        dev = self._dev()
        p._handle_multilevel(dev, self._raw_temp(70, 0, 1))   # scale=1 = degF
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 21.1, places=1)
        self.assertIn("degC", dev.state_writes["temperature"]["uiValue"])


# ==============================================================================
# Tests: Wake-up handling
# ==============================================================================

class TestHandleWakeUp(unittest.TestCase):
    """CC=0x84 — notification and interval report."""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Battery Sensor", address="10",
                          plugin_props={"sensorType": "motion"})

    def test_wake_up_notification_touches_device(self):
        """WAKE_UP_NOTIFICATION (0x84, 0x07) updates lastUpdate."""
        dev = self._dev()
        result = self.p._handle_wake_up(dev, 0x07, [0x84, 0x07])
        self.assertTrue(result)
        self.assertIn("lastUpdate", dev.state_writes)

    def test_wake_up_interval_report_stores_state(self):
        """WAKE_UP_INTERVAL_REPORT (0x84, 0x06) stores interval in seconds."""
        # 300 seconds = 0x00 0x01 0x2C
        dev = self._dev()
        result = self.p._handle_wake_up(dev, 0x06, [0x84, 0x06, 0x00, 0x01, 0x2C, 0x01])
        self.assertTrue(result)
        self.assertEqual(dev.state_writes["wakeUpInterval"]["value"], 300)

    def test_wake_up_interval_too_short_returns_false(self):
        """Truncated INTERVAL_REPORT (< 5 bytes) returns False."""
        dev = self._dev()
        result = self.p._handle_wake_up(dev, 0x06, [0x84, 0x06, 0x00])
        self.assertFalse(result)

    def test_wake_up_unknown_cmd_returns_false(self):
        """Unknown WAKE_UP sub-command returns False without crashing."""
        dev = self._dev()
        result = self.p._handle_wake_up(dev, 0xFF, [0x84, 0xFF])
        self.assertFalse(result)


# ==============================================================================
# Tests: Stale device detection
# ==============================================================================

class TestStaleDetection(unittest.TestCase):

    def setUp(self):
        self.p        = make_plugin()
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict

    def _dev(self, last_update="", dev_id=1):
        return MockDevice(dev_id, f"Sensor{dev_id}", address="50",
                          states={"lastUpdate": last_update},
                          plugin_props={"sensorType": "motion"})

    def _ts(self, hours_ago=0):
        dt = datetime.now() - timedelta(hours=hours_ago)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def test_no_last_update_not_flagged(self):
        """Device with no lastUpdate is skipped — cannot determine staleness."""
        dev = self._dev(last_update="")
        self.dev_dict[dev.id] = dev
        self.p._check_stale_devices()
        self.assertNotIn("deviceOnline", dev.state_writes)
        self.assertEqual(len(self.p.stale_device_ids), 0)

    def test_fresh_device_not_stale(self):
        """Device updated 1 hour ago (threshold 24h) is not flagged."""
        dev = self._dev(last_update=self._ts(hours_ago=1))
        self.dev_dict[dev.id] = dev
        self.p._check_stale_devices()
        self.assertNotIn("deviceOnline", dev.state_writes)
        self.assertNotIn(dev.id, self.p.stale_device_ids)

    def test_stale_device_flagged(self):
        """Device last updated 30h ago (threshold 24h) is flagged offline."""
        dev = self._dev(last_update=self._ts(hours_ago=30))
        self.dev_dict[dev.id] = dev
        self.p._check_stale_devices()
        self.assertFalse(dev.state_writes["deviceOnline"]["value"])
        self.assertIn(dev.id, self.p.stale_device_ids)
        self.p.logger.warning.assert_called()

    def test_stale_not_repeated(self):
        """Already-flagged device does not generate a second warning."""
        dev = self._dev(last_update=self._ts(hours_ago=30))
        self.dev_dict[dev.id] = dev
        self.p.stale_device_ids.add(dev.id)   # pre-flag it
        self.p._check_stale_devices()
        self.p.logger.warning.assert_not_called()

    def test_stale_detection_disabled(self):
        """With stale_enabled=False, no devices are checked."""
        self.p.stale_enabled = False
        dev = self._dev(last_update=self._ts(hours_ago=100))
        self.dev_dict[dev.id] = dev
        self.p._check_stale_devices()
        self.assertNotIn("deviceOnline", dev.state_writes)

    def test_touch_clears_stale_flag(self):
        """_touch() on a flagged device clears the flag and sets deviceOnline=True."""
        dev = self._dev()
        self.p.stale_device_ids.add(dev.id)
        self.p._touch(dev)
        self.assertNotIn(dev.id, self.p.stale_device_ids)
        self.assertTrue(dev.state_writes["deviceOnline"]["value"])


# ==============================================================================
# Tests: raw Z-Wave parsers (_handle_* methods)
# All byte sequences follow the Z-Wave specification.
# ==============================================================================

class TestHandleMultilevel(unittest.TestCase):
    """
    SENSOR_MULTILEVEL_REPORT (CC=0x31 CMD=0x05)
    prec_scale_size layout:  bits[7:5]=precision  bits[4:3]=scale  bits[2:0]=size
    value = signed_big_endian_integer / 10^precision
    """

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self, sensor_type="generic"):
        return MockDevice(1, "Test Device", address="223",
                          plugin_props={"sensorType": sensor_type})

    def _prec_scale_size(self, precision, scale, size):
        return (precision << 5) | (scale << 3) | size

    def test_temperature_21_5_degC(self):
        """21.5 degC: sensor=0x01, precision=1, scale=0(C), size=2, raw_int=215"""
        pss = self._prec_scale_size(1, 0, 2)
        raw = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 215))
        dev = self._dev("temperature")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 21.5)
        self.assertEqual(dev.state_writes["temperature"]["uiValue"], "21.5 degC")

    def test_temperature_70_degF(self):
        """70 degF reported, pref=degF -> stored as 70.0 degF (no conversion)."""
        p   = make_plugin(debug=True, temp_unit="degF")
        pss = self._prec_scale_size(0, 1, 1)
        raw = [0x31, 0x05, 0x01, pss, 70]
        dev = self._dev("temperature")
        self.assertTrue(p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], 70.0)
        self.assertIn("degF", dev.state_writes["temperature"]["uiValue"])

    def test_temperature_icon_from_raw_path(self):
        """Raw Z-Wave temperature report sets TemperatureSensor icon."""
        pss = self._prec_scale_size(1, 0, 2)
        raw = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", 200))
        dev = self._dev("temperature")
        self.p._handle_multilevel(dev, raw)
        self.assertIn("TemperatureSensor", dev.image_writes)
        self.assertNotIn("SensorOn", dev.image_writes)

    def test_luminance_450_lux(self):
        """450 lux: sensor=0x03, precision=0, scale=1(lux), size=2, raw_int=450"""
        pss = self._prec_scale_size(0, 1, 2)
        raw = [0x31, 0x05, 0x03, pss] + list(struct.pack(">h", 450))
        dev = self._dev("luminance")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["luminance"]["value"], 450.0)
        self.assertIn("lux", dev.state_writes["luminance"]["uiValue"])

    def test_luminance_icon_from_raw_path(self):
        """Raw Z-Wave luminance report sets LightSensor icon."""
        pss = self._prec_scale_size(0, 1, 2)
        raw = [0x31, 0x05, 0x03, pss] + list(struct.pack(">h", 200))
        dev = self._dev("luminance")
        self.p._handle_multilevel(dev, raw)
        self.assertIn("LightSensor", dev.image_writes)
        self.assertNotIn("SensorOn", dev.image_writes)

    def test_humidity_65_pct(self):
        """65%: sensor=0x05, precision=0, scale=0, size=1, raw_int=65"""
        pss = self._prec_scale_size(0, 0, 1)
        raw = [0x31, 0x05, 0x05, pss, 65]
        dev = self._dev("humidity")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["humidity"]["value"], 65.0)

    def test_humidity_icon_from_raw_path(self):
        """Raw Z-Wave humidity report sets HumiditySensor icon."""
        pss = self._prec_scale_size(0, 0, 1)
        raw = [0x31, 0x05, 0x05, pss, 55]
        dev = self._dev("humidity")
        self.p._handle_multilevel(dev, raw)
        self.assertIn("HumiditySensor", dev.image_writes)
        self.assertNotIn("SensorOn", dev.image_writes)

    def test_co2_850_ppm(self):
        """850 ppm CO2: sensor=0x0F, precision=0, scale=0, size=2"""
        pss = self._prec_scale_size(0, 0, 2)
        raw = [0x31, 0x05, 0x0F, pss] + list(struct.pack(">H", 850))
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["co2Level"]["value"], 850.0)

    def test_negative_temperature(self):
        """-5.0 degC: raw_int=-50, precision=1"""
        pss = self._prec_scale_size(1, 0, 2)
        raw = [0x31, 0x05, 0x01, pss] + list(struct.pack(">h", -50))
        dev = self._dev("temperature")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
        self.assertAlmostEqual(dev.state_writes["temperature"]["value"], -5.0)

    def test_unknown_sensor_type_returns_false(self):
        """Unknown sensor type byte logs info and returns False."""
        pss = self._prec_scale_size(0, 0, 1)
        raw = [0x31, 0x05, 0xFF, pss, 0x42]
        dev = self._dev("generic")
        self.assertFalse(self.p._handle_multilevel(dev, raw))
        self.p.logger.info.assert_called()

    def test_too_short_returns_false(self):
        """Truncated frame (< 5 bytes) returns False without crashing."""
        self.assertFalse(self.p._handle_multilevel(self._dev(), [0x31, 0x05, 0x01]))


class TestHandleBinarySensor(unittest.TestCase):
    """SENSOR_BINARY_REPORT (CC=0x30 CMD=0x03)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self, sensor_type="generic"):
        return MockDevice(1, "Test", address="223",
                          plugin_props={"sensorType": sensor_type})

    def test_motion_detected(self):
        """0xFF + type=0x08 (PIR) -> motion=True, displayStatus=detected."""
        dev = self._dev("motion")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x08]))
        self.assertTrue(dev.state_writes["motion"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "detected")

    def test_motion_clear(self):
        """0x00 + type=0x08 -> motion=False, displayStatus=clear."""
        dev = self._dev("motion")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0x00, 0x08]))
        self.assertFalse(dev.state_writes["motion"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "clear")

    def test_contact_open(self):
        """0xFF + type=0x0A -> contact=True, displayStatus=open."""
        dev = self._dev("contact")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x0A]))
        self.assertTrue(dev.state_writes["contact"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "open")

    def test_contact_closed(self):
        """0x00 + type=0x0A -> contact=False, displayStatus=closed."""
        dev = self._dev("contact")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0x00, 0x0A]))
        self.assertFalse(dev.state_writes["contact"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "closed")

    def test_water_leak(self):
        """0xFF + type=0x04 -> waterLeak=True, displayStatus=leak."""
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x04]))
        self.assertTrue(dev.state_writes["waterLeak"]["value"])
        self.assertEqual(dev.state_writes["waterLeak"]["uiValue"], "leak")

    def test_smoke_alarm(self):
        """0xFF + type=0x02 -> smoke=True."""
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x02]))
        self.assertTrue(dev.state_writes["smoke"]["value"])

    def test_tamper(self):
        """0xFF + type=0x06 -> tamper=True."""
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF, 0x06]))
        self.assertTrue(dev.state_writes["tamper"]["value"])

    def test_v1_no_type_byte_fallback(self):
        """v1 frame (no sensor type byte) falls back to onOffState."""
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_binary_sensor(dev, [0x30, 0x03, 0xFF]))
        self.assertTrue(dev.state_writes["onOffState"]["value"])

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_binary_sensor(self._dev(), [0x30, 0x03]))


class TestHandleNotification(unittest.TestCase):
    """NOTIFICATION_REPORT v4+ (CC=0x71 CMD=0x05)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self, sensor_type="generic"):
        return MockDevice(1, "Test", address="223",
                          plugin_props={"sensorType": sensor_type})

    def _notif(self, notif_type, notif_event, notif_status=0xFF):
        """Build a minimal 9-byte NOTIFICATION_REPORT frame."""
        return [0x71, 0x05, 0x00, 0x00, 0x00,
                notif_type, notif_status, notif_event, 0x00]

    # HOME_SECURITY (0x07)
    def test_home_security_motion_detected(self):
        dev = self._dev("motion")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x07, 0x07)))
        self.assertTrue(dev.state_writes["motion"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "detected")

    def test_home_security_motion_cleared(self):
        dev = self._dev("motion")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x07, 0x08)))
        self.assertFalse(dev.state_writes["motion"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "clear")

    def test_home_security_tamper(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x07, 0x03)))
        self.assertTrue(dev.state_writes["tamper"]["value"])

    def test_home_security_idle_clears_all(self):
        """Event=0x00 (idle) resets motion and tamper."""
        dev = self._dev("motion")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x07, 0x00)))
        self.assertFalse(dev.state_writes["motion"]["value"])
        self.assertFalse(dev.state_writes["tamper"]["value"])

    # ACCESS_CONTROL (0x06)
    def test_access_control_door_open(self):
        dev = self._dev("contact")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x06, 0x16)))
        self.assertTrue(dev.state_writes["contact"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "open")

    def test_access_control_door_closed(self):
        dev = self._dev("contact")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x06, 0x17)))
        self.assertFalse(dev.state_writes["contact"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "closed")

    # WATER (0x05)
    def test_water_leak_event_01(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x05, 0x01)))
        self.assertTrue(dev.state_writes["waterLeak"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "leak")

    def test_water_leak_cleared(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x05, 0x00)))
        self.assertFalse(dev.state_writes["waterLeak"]["value"])

    # SMOKE (0x01)
    def test_smoke_detected(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x01, 0x01)))
        self.assertTrue(dev.state_writes["smoke"]["value"])

    def test_smoke_cleared(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x01, 0x00)))
        self.assertFalse(dev.state_writes["smoke"]["value"])

    # CO (0x02)
    def test_co_alarm(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x02, 0x01)))
        self.assertTrue(dev.state_writes["coAlarm"]["value"])
        self.assertEqual(dev.state_writes["coAlarm"]["uiValue"], "alarm")

    def test_co_cleared(self):
        dev = self._dev("generic")
        self.assertTrue(self.p._handle_notification(dev, self._notif(0x02, 0x00)))
        self.assertFalse(dev.state_writes["coAlarm"]["value"])

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_notification(self._dev(), [0x71, 0x05, 0x00]))

    def test_unknown_notification_type_returns_false(self):
        dev = self._dev("generic")
        result = self.p._handle_notification(dev, self._notif(0xAA, 0x01))
        self.assertFalse(result)
        self.p.logger.info.assert_called()


class TestHandleBattery(unittest.TestCase):
    """BATTERY_REPORT (CC=0x80 CMD=0x03)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Test", address="223",
                          plugin_props={"sensorType": "generic"})

    def test_normal_level_85(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_battery(dev, [0x80, 0x03, 85]))
        self.assertEqual(dev.state_writes["batteryLevel"]["value"],   85)
        self.assertEqual(dev.state_writes["batteryLevel"]["uiValue"], "85%")

    def test_low_warning_0xFF(self):
        """0xFF is the Z-Wave battery-low sentinel -> value=1, uiValue=LOW."""
        dev = self._dev()
        self.assertTrue(self.p._handle_battery(dev, [0x80, 0x03, 0xFF]))
        self.assertEqual(dev.state_writes["batteryLevel"]["value"],   1)
        self.assertEqual(dev.state_writes["batteryLevel"]["uiValue"], "LOW")
        self.p.logger.warning.assert_called()

    def test_zero_percent(self):
        """0x00 is a valid 0% reading (distinct from the 0xFF sentinel)."""
        dev = self._dev()
        self.assertTrue(self.p._handle_battery(dev, [0x80, 0x03, 0x00]))
        self.assertEqual(dev.state_writes["batteryLevel"]["value"], 0)

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_battery(self._dev(), [0x80, 0x03]))


class TestHandleMeter(unittest.TestCase):
    """METER_REPORT v2 (CC=0x32 CMD=0x02)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Test", address="50",
                          plugin_props={"sensorType": "energy"})

    def _pss(self, precision, scale, size):
        return (precision << 5) | (scale << 3) | size

    def test_watts_2_0(self):
        """Electric power 2.0 W: precision=1, scale=2(W), size=2, raw_int=20"""
        raw = [0x32, 0x02, 0x01, self._pss(1, 2, 2)] + list(struct.pack(">h", 20))
        dev = self._dev()
        self.assertTrue(self.p._handle_meter(dev, raw))
        self.assertAlmostEqual(dev.state_writes["watts"]["value"], 2.0, places=3)
        self.assertIn("W", dev.state_writes["watts"]["uiValue"])

    def test_kwh_1_234(self):
        """Electric energy 1.234 kWh: precision=3, scale=0(kWh), size=4, raw_int=1234"""
        raw = [0x32, 0x02, 0x01, self._pss(3, 0, 4)] + list(struct.pack(">i", 1234))
        dev = self._dev()
        self.assertTrue(self.p._handle_meter(dev, raw))
        self.assertAlmostEqual(dev.state_writes["kwh"]["value"], 1.234, places=3)

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_meter(self._dev(), [0x32, 0x02, 0x01]))


class TestHandleSwitchBinary(unittest.TestCase):
    """SWITCH_BINARY_REPORT (CC=0x25 CMD=0x03)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Test", address="30",
                          plugin_props={"sensorType": "generic"})

    def test_switch_on(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_switch_binary(dev, [0x25, 0x03, 0xFF]))
        self.assertTrue(dev.state_writes["switchState"]["value"])
        self.assertTrue(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "on")

    def test_switch_off(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_switch_binary(dev, [0x25, 0x03, 0x00]))
        self.assertFalse(dev.state_writes["switchState"]["value"])
        self.assertFalse(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "off")

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_switch_binary(self._dev(), [0x25, 0x03]))


class TestHandleSwitchMultilevel(unittest.TestCase):
    """SWITCH_MULTILEVEL_REPORT (CC=0x26 CMD=0x03)"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Test", address="30",
                          plugin_props={"sensorType": "generic"})

    def test_dim_50_pct(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_switch_multilevel(dev, [0x26, 0x03, 50]))
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 50)
        self.assertTrue(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "50%")

    def test_dim_off(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_switch_multilevel(dev, [0x26, 0x03, 0x00]))
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 0)
        self.assertFalse(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "off")

    def test_0xFF_means_99_pct(self):
        """0xFF = restore last non-zero level — plugin treats as 99%."""
        dev = self._dev()
        self.assertTrue(self.p._handle_switch_multilevel(dev, [0x26, 0x03, 0xFF]))
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 99)

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_switch_multilevel(self._dev(), [0x26, 0x03]))


class TestHandleBasic(unittest.TestCase):
    """BASIC_REPORT (CC=0x20 CMD=0x03) — legacy command class"""

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Test", address="30",
                          plugin_props={"sensorType": "generic"})

    def test_basic_on_0xFF(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_basic(dev, [0x20, 0x03, 0xFF]))
        self.assertTrue(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 99)

    def test_basic_off(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_basic(dev, [0x20, 0x03, 0x00]))
        self.assertFalse(dev.state_writes["onOffState"]["value"])
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 0)

    def test_basic_dim_50(self):
        dev = self._dev()
        self.assertTrue(self.p._handle_basic(dev, [0x20, 0x03, 50]))
        self.assertEqual(dev.state_writes["dimLevel"]["value"], 50)
        self.assertTrue(dev.state_writes["onOffState"]["value"])

    def test_too_short_returns_false(self):
        self.assertFalse(self.p._handle_basic(self._dev(), [0x20, 0x03]))


# ==============================================================================
# Tests: startup() — subscribeToIncoming() called
# ==============================================================================

class TestStartup(unittest.TestCase):
    """Verify startup() calls indigo.zwave.subscribeToIncoming()."""

    def setUp(self):
        self.p = make_plugin()
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict
        _indigo.zwave   = MagicMock()

    def test_subscribe_to_incoming_called(self):
        """startup() must call subscribeToIncoming() to receive all Z-Wave bytes."""
        self.p.startup()
        _indigo.zwave.subscribeToIncoming.assert_called_once()

    def test_node_map_built_on_startup(self):
        """startup() rebuilds the node->device map from existing plugin devices."""
        dev = MockDevice(1, "Sensor", address="42",
                         plugin_id="com.clives.universal-zwave-sensor",
                         plugin_props={"nodeId": "42"})
        self.dev_dict[1] = dev
        self.p.startup()
        self.assertIn(42, self.p.node_to_device)


# ==============================================================================
# Tests: get_native_zwave_devices() callback
# ==============================================================================

class TestGetNativeZwaveDevices(unittest.TestCase):

    def setUp(self):
        self.p        = make_plugin()
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict

    def _add(self, dev_id, name, address, plugin_id="com.perceptiveautomation.indigoplugin.zwave"):
        dev = MockDevice(dev_id, name, address=address, plugin_id=plugin_id)
        self.dev_dict[dev_id] = dev
        return dev

    def test_returns_native_zwave_devices(self):
        """Native Z-Wave devices with numeric addresses are returned."""
        self._add(1, "Front Door", "42")
        self._add(2, "Back Door",  "55")
        result = self.p.get_native_zwave_devices()
        ids = [r[0] for r in result]
        self.assertIn("1", ids)
        self.assertIn("2", ids)

    def test_excludes_own_plugin_devices(self):
        """Our own plugin devices are excluded from the list."""
        self._add(10, "Plugin Sensor", "42",
                  plugin_id="com.clives.universal-zwave-sensor")
        result = self.p.get_native_zwave_devices()
        ids = [r[0] for r in result]
        self.assertNotIn("10", ids)

    def test_excludes_non_numeric_addresses(self):
        """Devices with non-numeric addresses (not Z-Wave) are excluded."""
        self._add(20, "HA Device", "binary_sensor.hall",
                  plugin_id="no.homeassistant.plugin")
        result = self.p.get_native_zwave_devices()
        ids = [r[0] for r in result]
        self.assertNotIn("20", ids)

    def test_empty_returns_placeholder(self):
        """When no native Z-Wave devices exist, returns the 'none' placeholder."""
        result = self.p.get_native_zwave_devices()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "none")

    def test_label_includes_name_and_node(self):
        """Each entry label includes the device name and node ID."""
        self._add(5, "Hall Motion", "77")
        result = self.p.get_native_zwave_devices()
        labels = [r[1] for r in result]
        self.assertTrue(any("Hall Motion" in l and "77" in l for l in labels))


# ==============================================================================
# Tests: NOTIFICATION byte order auto-detection
# ==============================================================================

class TestNotificationByteOrderDetection(unittest.TestCase):
    """
    The plugin auto-detects whether hardware uses:
      Spec order:     [status(0xFF/0x00), type, event]  at raw[5..7]  — standard hardware
      Reversed order: [type, status(0xFF/0x00), event]  at raw[5..7]  — some older devices
    Detection: if raw[5] in (0x00, 0xFF) -> spec order; else -> reversed order.
    """

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dev(self):
        return MockDevice(1, "Door Sensor", address="156",
                          plugin_props={"sensorType": "contact"})

    def test_spec_order_door_open(self):
        """Spec order (0xFF at raw[5]): ACCESS_CONTROL door open — macpro's sensor format."""
        # 71 05 00 00 00 FF 06 16 00  (status=0xFF, type=0x06, event=0x16)
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0xFF, 0x06, 0x16, 0x00]
        dev = self._dev()
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertTrue(dev.state_writes["contact"]["value"])
        self.assertEqual(dev.state_writes["displayStatus"]["value"], "open")

    def test_spec_order_door_closed(self):
        """Spec order: ACCESS_CONTROL door closed."""
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0xFF, 0x06, 0x17, 0x00]
        dev = self._dev()
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertFalse(dev.state_writes["contact"]["value"])

    def test_spec_order_motion_detected(self):
        """Spec order: HOME_SECURITY motion detected."""
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0xFF, 0x07, 0x07, 0x00]
        dev = MockDevice(1, "Motion", address="156",
                         plugin_props={"sensorType": "motion"})
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertTrue(dev.state_writes["motion"]["value"])

    def test_spec_order_status_0x00_idle(self):
        """Spec order with status=0x00 (inactive): HOME_SECURITY idle."""
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0x00, 0x07, 0x00, 0x00]
        dev = MockDevice(1, "Motion", address="156",
                         plugin_props={"sensorType": "motion"})
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertFalse(dev.state_writes["motion"]["value"])

    def test_reversed_order_motion_detected(self):
        """Reversed order (type at raw[5]): HOME_SECURITY motion detected — older devices."""
        # 71 05 00 00 00 07 FF 07 00  (type=0x07, status=0xFF, event=0x07)
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0x07, 0xFF, 0x07, 0x00]
        dev = MockDevice(1, "Motion", address="10",
                         plugin_props={"sensorType": "motion"})
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertTrue(dev.state_writes["motion"]["value"])

    def test_reversed_order_door_open(self):
        """Reversed order: ACCESS_CONTROL door open."""
        raw = [0x71, 0x05, 0x00, 0x00, 0x00, 0x06, 0xFF, 0x16, 0x00]
        dev = self._dev()
        self.assertTrue(self.p._handle_notification(dev, raw))
        self.assertTrue(dev.state_writes["contact"]["value"])


# ==============================================================================
# Tests: serial API frame unwrapping in _extract_node_and_bytes
# ==============================================================================

class TestExtractNodeAndBytes(unittest.TestCase):
    """
    When subscribeToIncoming() is active, Indigo delivers the full Z-Wave
    serial API frame. _extract_node_and_bytes() must unwrap it.
    Frame: [01, LEN, 00, 04, rxStatus, srcNode, cmdLen, cmd_bytes..., checksum]
    """

    def setUp(self):
        self.p = make_plugin()

    def _cmd(self, node_id, raw_bytes):
        """Build a mock cmd dict as Indigo delivers it."""
        mock_cmd = MagicMock()
        mock_cmd.get = lambda key, default=None: {
            "nodeId":  node_id,
            "bytes":   raw_bytes,
        }.get(key, default)
        return mock_cmd

    def _serial_frame(self, node_id, payload):
        """Wrap a Z-Wave payload in a serial API APPLICATION_COMMAND_HANDLER frame."""
        cmd_len = len(payload)
        body    = [0x00, 0x04, 0x00, node_id, cmd_len] + list(payload)
        length  = len(body) + 1   # body + checksum byte
        frame   = [0x01, length] + body + [0xFF]   # 0xFF = dummy checksum
        return frame

    def test_serial_frame_unwrapped_correctly(self):
        """Temperature report wrapped in serial API frame is unwrapped to raw payload."""
        payload = [0x31, 0x05, 0x01, 0x22, 0x00, 0xDA]   # 21.8 degC
        frame   = self._serial_frame(106, payload)
        node_id, raw = self.p._extract_node_and_bytes(self._cmd(106, frame))
        self.assertEqual(node_id, 106)
        self.assertEqual(raw, payload)

    def test_plain_bytes_passed_through_unchanged(self):
        """Bytes that are already a Z-Wave command (no serial framing) pass through unchanged."""
        payload = [0x31, 0x05, 0x01, 0x22, 0x00, 0xD7]   # 21.5 degC
        node_id, raw = self.p._extract_node_and_bytes(self._cmd(50, payload))
        self.assertEqual(node_id, 50)
        self.assertEqual(raw, payload)

    def test_notification_frame_unwrapped(self):
        """NOTIFICATION report wrapped in serial API frame is unwrapped correctly."""
        payload = [0x71, 0x05, 0x00, 0x00, 0x00, 0xFF, 0x07, 0x07, 0x00]
        frame   = self._serial_frame(106, payload)
        node_id, raw = self.p._extract_node_and_bytes(self._cmd(106, frame))
        self.assertEqual(raw, payload)

    def test_truncated_frame_falls_through_safely(self):
        """A truncated or malformed frame is returned as-is rather than crashing."""
        frame = [0x01, 0x08, 0x00, 0x04, 0x00, 0x6A]   # header only, no cmd_len byte
        node_id, raw = self.p._extract_node_and_bytes(self._cmd(106, frame))
        self.assertEqual(raw, frame)   # unchanged — no crash


# ==============================================================================
# Entry point
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

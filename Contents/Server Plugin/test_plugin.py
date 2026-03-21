#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    test_plugin.py
# Description: Mock test suite for Universal Z-Wave Sensor plugin v1.5
#              Covers: _mirror_from_device (subscribeToChanges path),
#                      all raw Z-Wave parsers (_handle_* methods),
#                      deviceUpdated filtering, deviceStartComm initial sync.
# Author:      CliveS & Claude Sonnet 4.6
# Date:        21-03-2026
# Version:     1.0
#
# Run from the Server Plugin directory:
#   python test_plugin.py -v

import os
import sys
import struct
import unittest
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
        self._on_state   = on_state     # None  =>  device has no onState attribute

        # Capture all writes during the test
        self.state_writes = {}          # key -> {"value": v, "uiValue": u}
        self.image_writes = []          # list of image selector strings

    def __repr__(self):
        return f"MockDevice(id={self.id}, name={self.name!r})"

    def updateStateOnServer(self, key, value=None, uiValue=None):
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
    """Supports indigo.devices[id] lookups and indigo.devices.iter('self')."""
    def iter(self, filter_str=""):
        return list(self.values())


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

def make_plugin(debug=False):
    p = _plugin_mod.Plugin.__new__(_plugin_mod.Plugin)
    p.debug          = debug
    p.log_unknown    = True
    p.pluginId       = "com.clives.universal-zwave-sensor"
    p.node_to_device = {}
    p.logger         = MagicMock()
    return p


# ==============================================================================
# Tests: _mirror_from_device  (subscribeToChanges / known-device path)
# ==============================================================================

class TestMirrorTemperature(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dest(self, source_id=""):
        return MockDevice(10, "223 temperature sensor", address="223",
                          plugin_props={"sensorType": "temperature",
                                        "sourceDeviceId": source_id})

    def test_named_temperature_key(self):
        """'temperature' state key -> temperature written with degC uiValue."""
        src  = MockDevice(1, "Temp", address="223", states={"temperature": 21.5})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["temperature"]["value"],   21.5)
        self.assertEqual(dest.state_writes["temperature"]["uiValue"], "21.5 degC")

    def test_sensorValue_with_source_filter(self):
        """sensorValue used as temperature only when sourceDeviceId is set."""
        src  = MockDevice(1, "Temp", address="223", states={"sensorValue": 19.3})
        dest = self._dest(source_id="1")
        self.p._mirror_from_device(dest, src)
        self.assertAlmostEqual(dest.state_writes["temperature"]["value"], 19.3)

    def test_sensorValue_without_source_filter_is_ignored(self):
        """sensorValue NOT used for temperature when sourceDeviceId is blank -> logs warning."""
        src  = MockDevice(1, "Lux", address="223", states={"sensorValue": 67.0})
        dest = self._dest(source_id="")
        self.p._mirror_from_device(dest, src)
        self.assertNotIn("temperature", dest.state_writes)
        self.p.logger.warning.assert_called()

    def test_displayStatus_set_for_temperature_type(self):
        """displayStatus shows 'X.X degC' for a temperature-type device."""
        src  = MockDevice(1, "Temp", address="223", states={"temperature": 18.7})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "18.7 degC")

    def test_temperature_icon(self):
        """Temperature device gets TemperatureSensor icon (not SensorOn)."""
        src  = MockDevice(1, "Temp", address="223", states={"temperature": 20.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("TemperatureSensor", dest.image_writes)
        self.assertNotIn("SensorOn", dest.image_writes)


class TestMirrorLuminance(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dest(self, source_id="2"):
        return MockDevice(11, "223 lux sensor", address="223",
                          plugin_props={"sensorType": "luminance",
                                        "sourceDeviceId": source_id})

    def test_sensorValue_maps_to_luminance(self):
        """sensorValue on a lux source writes luminance state in lux."""
        src  = MockDevice(2, "Lux", address="223", states={"sensorValue": 450.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["luminance"]["value"],   450.0)
        self.assertEqual(dest.state_writes["luminance"]["uiValue"], "450 lux")

    def test_illuminance_key(self):
        """Named 'illuminance' state also maps to luminance."""
        src  = MockDevice(2, "Lux", address="223", states={"illuminance": 120.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["luminance"]["value"], 120.0)

    def test_luminance_displayStatus(self):
        """displayStatus shows 'N lux' for a luminance-type device."""
        src  = MockDevice(2, "Lux", address="223", states={"illuminance": 200.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "200 lux")

    def test_luminance_icon(self):
        """Luminance device gets LightSensor icon."""
        src  = MockDevice(2, "Lux", address="223", states={"illuminance": 100.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("LightSensor", dest.image_writes)
        self.assertNotIn("SensorOn", dest.image_writes)

    def test_lux_device_does_not_write_temperature(self):
        """Lux plugin device + lux source: luminance written, temperature NOT written."""
        src  = MockDevice(2, "Lux", address="223", states={"sensorValue": 67.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("luminance", dest.state_writes)
        self.assertNotIn("temperature", dest.state_writes)


class TestMirrorHumidity(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dest(self):
        return MockDevice(12, "223 humidity sensor", address="223",
                          plugin_props={"sensorType": "humidity", "sourceDeviceId": ""})

    def test_humidity_value_and_uiValue(self):
        src  = MockDevice(3, "Humidity", address="223", states={"humidity": 65.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["humidity"]["value"],   65.0)
        self.assertEqual(dest.state_writes["humidity"]["uiValue"], "65%")

    def test_humidity_icon(self):
        """Humidity device gets HumiditySensor icon (not SensorOn)."""
        src  = MockDevice(3, "Humidity", address="223", states={"humidity": 50.0})
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("HumiditySensor", dest.image_writes)
        self.assertNotIn("SensorOn", dest.image_writes)


class TestMirrorMotion(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dest(self):
        return MockDevice(13, "223 motion sensor", address="223",
                          plugin_props={"sensorType": "motion", "sourceDeviceId": "4"})

    def test_motion_detected(self):
        src  = MockDevice(4, "Motion", address="223", on_state=True)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertTrue(dest.state_writes["onOffState"]["value"])
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "detected")

    def test_motion_clear(self):
        src  = MockDevice(4, "Motion", address="223", on_state=False)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertFalse(dest.state_writes["onOffState"]["value"])
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "clear")

    def test_motion_icon_detected(self):
        src  = MockDevice(4, "Motion", address="223", on_state=True)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("MotionSensorTripped", dest.image_writes)

    def test_motion_icon_clear(self):
        src  = MockDevice(4, "Motion", address="223", on_state=False)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertIn("MotionSensor", dest.image_writes)


class TestMirrorContact(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def _dest(self):
        return MockDevice(14, "100 contact sensor", address="100",
                          plugin_props={"sensorType": "contact", "sourceDeviceId": "5"})

    def test_contact_open(self):
        src  = MockDevice(5, "Door", address="100", on_state=True)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "open")

    def test_contact_closed(self):
        src  = MockDevice(5, "Door", address="100", on_state=False)
        dest = self._dest()
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["displayStatus"]["value"], "closed")


class TestMirrorEnergyAndBattery(unittest.TestCase):

    def setUp(self):
        self.p = make_plugin(debug=True)

    def test_watts(self):
        src  = MockDevice(7, "Power", address="50", states={"curEnergyLevel": 125.5})
        dest = MockDevice(16, "50 energy", address="50",
                          plugin_props={"sensorType": "energy", "sourceDeviceId": "7"})
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["watts"]["value"],   125.5)
        self.assertEqual(dest.state_writes["watts"]["uiValue"], "125.5 W")

    def test_kwh(self):
        src  = MockDevice(7, "Power", address="50", states={"energyAccumTotal": 1.234})
        dest = MockDevice(16, "50 energy", address="50",
                          plugin_props={"sensorType": "energy", "sourceDeviceId": "7"})
        self.p._mirror_from_device(dest, src)
        self.assertAlmostEqual(dest.state_writes["kwh"]["value"], 1.234, places=3)

    def test_battery_level(self):
        """Battery state written for any sensor type that reports batteryLevel."""
        src  = MockDevice(6, "Multi", address="223", states={"batteryLevel": 85})
        dest = MockDevice(13, "223 motion", address="223",
                          plugin_props={"sensorType": "motion", "sourceDeviceId": ""})
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["batteryLevel"]["value"],   85)
        self.assertEqual(dest.state_writes["batteryLevel"]["uiValue"], "85%")

    def test_dim_level(self):
        src  = MockDevice(8, "Dimmer", address="30", on_state=True,
                          states={"brightnessLevel": 75})
        dest = MockDevice(17, "30 dimmer", address="30",
                          plugin_props={"sensorType": "generic", "sourceDeviceId": "8"})
        self.p._mirror_from_device(dest, src)
        self.assertEqual(dest.state_writes["dimLevel"]["value"],   75)
        self.assertEqual(dest.state_writes["dimLevel"]["uiValue"], "75%")


# ==============================================================================
# Tests: deviceUpdated filtering
# ==============================================================================

class TestDeviceUpdatedFiltering(unittest.TestCase):

    def setUp(self):
        self.p        = make_plugin(debug=True)
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict

    def test_own_plugin_device_is_ignored(self):
        """Our own plugin devices must be skipped — prevents the feedback loop."""
        own = MockDevice(99, "223 motion sensor", address="223",
                         plugin_id="com.clives.universal-zwave-sensor")
        self.p.node_to_device = {223: [99]}
        self.p.deviceUpdated(own, own)
        self.assertEqual(own.state_writes, {})      # nothing written

    def test_unknown_node_is_ignored(self):
        """Devices on nodes we are not monitoring are silently skipped."""
        foreign = MockDevice(50, "Unmonitored Device", address="50",
                             plugin_id="some.other.plugin")
        self.p.node_to_device = {223: [10]}
        self.p.deviceUpdated(foreign, foreign)      # must not raise

    def test_source_filter_passes_matching_device(self):
        """sourceDeviceId set and matching -> mirror runs."""
        src  = MockDevice(5, "Front Door Temp", address="223",
                          plugin_id="com.perceptiveautomation.indigoplugin.zwave",
                          states={"temperature": 20.0})
        dest = MockDevice(10, "223 temp", address="223",
                          plugin_id="com.clives.universal-zwave-sensor",
                          plugin_props={"sensorType": "temperature",
                                        "sourceDeviceId": "5"})
        self.dev_dict[10] = dest
        self.p.node_to_device = {223: [10]}
        self.p.deviceUpdated(src, src)
        self.assertIn("temperature", dest.state_writes)

    def test_source_filter_blocks_wrong_source(self):
        """sourceDeviceId set but source id does not match -> mirror skipped."""
        wrong_src = MockDevice(99, "Lux Device", address="223",
                               plugin_id="com.perceptiveautomation.indigoplugin.zwave",
                               states={"sensorValue": 67.0})
        dest = MockDevice(10, "223 temp", address="223",
                          plugin_id="com.clives.universal-zwave-sensor",
                          plugin_props={"sensorType": "temperature",
                                        "sourceDeviceId": "5"})    # expects id=5
        self.dev_dict[10] = dest
        self.p.node_to_device = {223: [10]}
        self.p.deviceUpdated(wrong_src, wrong_src)
        self.assertEqual(dest.state_writes, {})     # blocked

    def test_no_source_filter_accepts_any_node_device(self):
        """No sourceDeviceId -> any native device on the node triggers a mirror."""
        src  = MockDevice(5, "Front Door Motion", address="223",
                          plugin_id="com.perceptiveautomation.indigoplugin.zwave",
                          on_state=True)
        dest = MockDevice(10, "223 motion", address="223",
                          plugin_id="com.clives.universal-zwave-sensor",
                          plugin_props={"sensorType": "motion", "sourceDeviceId": ""})
        self.dev_dict[10] = dest
        self.p.node_to_device = {223: [10]}
        self.p.deviceUpdated(src, src)
        self.assertIn("onOffState", dest.state_writes)


# ==============================================================================
# Tests: deviceStartComm initial state sync
# ==============================================================================

class TestDeviceStartComm(unittest.TestCase):

    def setUp(self):
        self.p        = make_plugin(debug=True)
        self.dev_dict = MockDevicesDict()
        _indigo.devices = self.dev_dict

    def test_initial_sync_reads_current_source_state(self):
        """deviceStartComm mirrors source device state immediately on startup."""
        src_dev = MockDevice(5, "Front Door Temp", address="223",
                             states={"temperature": 21.5})
        self.dev_dict[5] = src_dev
        plugin_dev = MockDevice(10, "223 temp", address="223",
                                plugin_props={"sensorType":    "temperature",
                                              "sourceDeviceId": "5",
                                              "nodeId":         "223"})
        self.dev_dict[10]         = plugin_dev
        _indigo.devices.iter      = lambda f="": [plugin_dev]
        self.p.deviceStartComm(plugin_dev)
        self.assertIn("temperature", plugin_dev.state_writes)
        self.assertAlmostEqual(plugin_dev.state_writes["temperature"]["value"], 21.5)

    def test_no_initial_sync_without_source_device(self):
        """No sourceDeviceId -> deviceStartComm does not write any states."""
        plugin_dev = MockDevice(10, "223 motion", address="223",
                                plugin_props={"sensorType":    "motion",
                                              "sourceDeviceId": "",
                                              "nodeId":         "223"})
        self.dev_dict[10]    = plugin_dev
        _indigo.devices.iter = lambda f="": [plugin_dev]
        self.p.deviceStartComm(plugin_dev)
        self.assertEqual(plugin_dev.state_writes, {})

    def test_missing_source_device_logs_warning(self):
        """sourceDeviceId points to a device that does not exist -> warning logged."""
        plugin_dev = MockDevice(10, "223 temp", address="223",
                                plugin_props={"sensorType":    "temperature",
                                              "sourceDeviceId": "999",
                                              "nodeId":         "223"})
        _indigo.devices.iter = lambda f="": [plugin_dev]
        self.p.deviceStartComm(plugin_dev)
        self.p.logger.warning.assert_called()


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
        """70 degF: sensor=0x01, precision=0, scale=1(F), size=1, raw_int=70"""
        pss = self._prec_scale_size(0, 1, 1)
        raw = [0x31, 0x05, 0x01, pss, 70]
        dev = self._dev("temperature")
        self.assertTrue(self.p._handle_multilevel(dev, raw))
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
# Entry point
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    plugin.py
# Description: Universal Z-Wave Sensor - creates companion plugin devices
#              alongside existing Indigo Z-Wave devices, capturing sensor values
#              (temperature, humidity, contact, etc.) that Indigo does not expose
#              natively. Uses subscribeToIncoming() to receive ALL Z-Wave bytes.
# Author:      CliveS & Claude Sonnet 4.6
# Date:        04-05-2026
# Version:     5.2

import indigo
import os as _os
import struct
import sys
import platform
from datetime import datetime, timedelta

sys.path.insert(0, _os.getcwd())
try:
    from plugin_utils import log_startup_banner
except ImportError:
    log_startup_banner = None


# ==============================================================================
# Z-Wave Command Class constants
# ==============================================================================

CC_BASIC                = 0x20
CC_SWITCH_BINARY        = 0x25
CC_SWITCH_MULTILEVEL    = 0x26
CC_SENSOR_BINARY        = 0x30
CC_SENSOR_MULTILEVEL    = 0x31
CC_METER                = 0x32
CC_CENTRAL_SCENE        = 0x5B   # central scene notifications (buttons, remotes)
CC_MULTI_CHANNEL        = 0x60   # multi-channel / endpoint encapsulation
CC_DOOR_LOCK            = 0x62
CC_NOTIFICATION         = 0x71   # replaces ALARM (0x9C) in v4+
CC_BATTERY              = 0x80
CC_WAKE_UP              = 0x84

# Command function codes (second byte in report)
CMD_BASIC_REPORT                = 0x03
CMD_SWITCH_BINARY_REPORT        = 0x03
CMD_SWITCH_MULTILEVEL_REPORT    = 0x03
CMD_SENSOR_BINARY_REPORT        = 0x03
CMD_SENSOR_MULTILEVEL_REPORT    = 0x05
CMD_METER_REPORT                = 0x02
CMD_NOTIFICATION_REPORT         = 0x05
CMD_BATTERY_REPORT              = 0x03
CMD_WAKE_UP_NOTIFICATION        = 0x07
CMD_WAKE_UP_INTERVAL_REPORT     = 0x06
CMD_MULTI_CHANNEL_ENCAP         = 0x0D
CMD_CENTRAL_SCENE_NOTIFICATION  = 0x03   # same opcode value as other *_REPORT commands
CMD_DOOR_LOCK_REPORT            = 0x03   # same opcode value as other *_REPORT commands

# ==============================================================================
# SENSOR_MULTILEVEL (0x31) sensor type lookup
# key  -> (state_id, default_unit)
# ==============================================================================
SENSOR_TYPES = {
    0x01: ("temperature",  "degC"),
    0x03: ("luminance",    "lux"),
    0x05: ("humidity",     "%"),
    0x08: ("pressure",     "kPa"),
    0x0B: ("velocity",     "m/s"),
    0x0F: ("co2Level",     "ppm"),
    0x10: ("watts",        "W"),    # power (reuses energy meter state)
    0x11: ("uvIndex",      ""),
    0x12: ("voltage",      "V"),    # reuses meter voltage state
    0x13: ("current",      "A"),    # reuses meter current state
    0x15: ("airFlow",      "m3/h"),
    0x19: ("voc",          "ppm"),
    0x1B: ("noise",        "dB"),
    0x1C: ("soilMoisture", "%"),
}

# ==============================================================================
# SENSOR_BINARY (0x30) sensor type lookup
# key  -> state_id
# ==============================================================================
BINARY_SENSOR_TYPES = {
    0x01: "onOffState",    # general purpose
    0x02: "smoke",
    0x03: "coAlarm",
    0x04: "waterLeak",
    0x06: "tamper",
    0x08: "motion",
    0x09: "motion",        # PIR alternative
    0x0A: "contact",       # door / window
    0x0B: "motion",        # movement alternative
    0x0C: "motion",        # motion sensor (Z-Wave SENSOR_BINARY v2 type 0x0C)
}

# ==============================================================================
# NOTIFICATION (0x71) type and event constants
# ==============================================================================
NOTIF_SMOKE            = 0x01
NOTIF_CO               = 0x02
NOTIF_WATER            = 0x05
NOTIF_ACCESS_CONTROL   = 0x06
NOTIF_HOME_SECURITY    = 0x07
NOTIF_POWER_MANAGEMENT = 0x08

# HOME_SECURITY events
HS_IDLE                = 0x00   # No event / all clear
HS_INTRUSION           = 0x01   # Intrusion, location provided
HS_INTRUSION_NL        = 0x02   # Intrusion, unknown location
HS_TAMPER              = 0x03   # Tampering — product covering removed
HS_GLASS_BREAK         = 0x05   # Glass break, location provided
HS_GLASS_BREAK_NL      = 0x06   # Glass break, unknown location
HS_MOTION_DETECTED     = 0x07   # Motion Detection, location provided
HS_MOTION_DETECTED_NL  = 0x08   # Motion Detection, unknown location
HS_TAMPER_ALT          = 0x09   # Tampering — product moved / alternate code

# ACCESS_CONTROL events — door/window open/close
AC_DOOR_OPEN           = 0x16
AC_DOOR_CLOSED         = 0x17
# ACCESS_CONTROL events — lock operations (fired by smart locks via NOTIFICATION)
AC_MANUAL_LOCK         = 0x01
AC_MANUAL_UNLOCK       = 0x02
AC_RF_LOCK             = 0x03
AC_RF_UNLOCK           = 0x04
AC_KEYPAD_LOCK         = 0x05
AC_KEYPAD_UNLOCK       = 0x06
AC_AUTO_LOCK           = 0x09
AC_LOCK_JAMMED         = 0x0B

# ==============================================================================
# METER (0x32) electric scale lookup
# key -> (state_id, unit)
# ==============================================================================
METER_ELECTRIC         = 0x01
METER_GAS              = 0x02
METER_WATER            = 0x03

METER_ELECTRIC_SCALES = {
    0: ("kwh",     "kWh"),
    1: ("kwh",     "kVAh"),
    2: ("watts",   "W"),
    # scale=3: pulse count (no useful state to write)
    # scale=4/5/6 use METER_REPORT v3 — Scale2 bit in byte 2 combines with 2-bit scale in byte 3
    4: ("voltage", "V"),
    5: ("current", "A"),
}

METER_GAS_SCALES = {
    0: ("gasCubicMeters", "m3"),
    1: ("gasCubicMeters", "ft3"),
    2: ("gasCubicMeters", "ccf"),
}

METER_WATER_SCALES = {
    0: ("waterCubicMeters", "m3"),
    1: ("waterCubicMeters", "gal"),
    2: ("waterCubicMeters", "ft3"),
}

# ==============================================================================
# NOTIFICATION (0x71) — POWER_MANAGEMENT event constants (type = NOTIF_POWER_MANAGEMENT)
# ==============================================================================
PM_POWER_APPLIED       = 0x01   # power has been applied
PM_AC_DISCONNECTED     = 0x02   # AC mains disconnected
PM_AC_RECONNECTED      = 0x03   # AC mains reconnected
PM_SURGE               = 0x04   # surge detected
PM_OVER_CURRENT        = 0x06   # over-current detected
PM_REPLACE_BATTERY     = 0x0A   # replace battery soon
PM_REPLACE_BATTERY_NOW = 0x0B   # replace battery now
PM_BATTERY_CHARGING    = 0x0C   # battery is charging
PM_BATTERY_CHARGED     = 0x0D   # battery is fully charged

# ==============================================================================
# CENTRAL_SCENE (0x5B) key attribute constants
# ==============================================================================
CS_KEY_PRESSED_1X  = 0x00   # single press
CS_KEY_RELEASED    = 0x01   # key released (after held)
CS_KEY_HELD_DOWN   = 0x02   # key held down (fires repeatedly)
CS_KEY_PRESSED_2X  = 0x03   # double press
CS_KEY_PRESSED_3X  = 0x04   # triple press
CS_KEY_PRESSED_4X  = 0x05   # quad press
CS_KEY_PRESSED_5X  = 0x06   # quint press

CENTRAL_SCENE_KEY_ACTIONS = {
    CS_KEY_PRESSED_1X: "pressed",
    CS_KEY_RELEASED:   "released",
    CS_KEY_HELD_DOWN:  "held",
    CS_KEY_PRESSED_2X: "double",
    CS_KEY_PRESSED_3X: "triple",
    CS_KEY_PRESSED_4X: "quad",
    CS_KEY_PRESSED_5X: "quint",
}

# ==============================================================================
# Device type ID -> sensor type string mapping
# New typed device types (v5.1+) use deviceTypeId; legacy zwaveSensor type
# reads from pluginProps["sensorType"] via _sensor_type() fallback.
# ==============================================================================
DEVICE_TYPE_SENSOR_TYPE = {
    "zwaveSensorMotion":      "motion",
    "zwaveSensorContact":     "contact",
    "zwaveSensorTemperature": "temperature",
    "zwaveSensorHumidity":    "humidity",
    "zwaveSensorLuminance":   "luminance",
    "zwaveSensorEnergy":      "energy",
    "zwaveSensorBattery":     "battery",
    "zwaveSensorLock":        "lock",
    "zwaveSensorScene":       "scene",
    "zwaveSensorGeneric":     "generic",
}


# ==============================================================================
# Plugin class
# ==============================================================================

class Plugin(indigo.PluginBase):

    def __init__(self, plugin_id, display_name, version, prefs):
        super().__init__(plugin_id, display_name, version, prefs)
        self.debug          = prefs.get("showDebugInfo",         False)
        self.log_unknown    = prefs.get("logUnknownReports",     True)
        self.temp_unit      = prefs.get("tempUnit",              "degC")
        self.stale_enabled  = prefs.get("enableStaleDetection",  True)
        self.stale_hours    = int(prefs.get("staleThresholdHours", 24))
        # Maps Z-Wave node_id (int) -> list of Indigo device_ids (int)
        # One physical Z-Wave node can back multiple plugin devices (motion, temp, lux...)
        self.node_to_device:   dict[int, list[int]] = {}
        # Set of device IDs currently flagged as stale (avoids repeated log warnings)
        self.stale_device_ids: set[int] = set()
        # Re-entry guard: stateListOrDisplayStateIdChanged() can cause Indigo to call
        # deviceStartComm again before the first call returns — this prevents that loop
        self._devices_starting: set[int] = set()

        # Banner logged here in __init__ using raw constructor params — the only reliable
        # point; PluginBase overwrites self.pluginVersion/pluginDisplayName by startup()
        title = " Starting Universal Z-Wave Sensor Plugin "
        width = 110
        col   = 28
        self.logger.info("=" * width)
        self.logger.info(title.center(width, "="))
        self.logger.info("=" * width)
        self.logger.info(f"{'Plugin Name:':<{col}} {display_name}")
        self.logger.info(f"{'Plugin Version:':<{col}} {version}")
        self.logger.info(f"{'Plugin ID:':<{col}} {plugin_id}")
        self.logger.info(f"{'Indigo Version:':<{col}} {indigo.server.version}")
        self.logger.info(f"{'Indigo API Version:':<{col}} {indigo.server.apiVersion}")
        self.logger.info(f"{'Architecture:':<{col}} {platform.machine()}")
        self.logger.info(f"{'Python Version:':<{col}} {platform.python_version()}")
        self.logger.info(f"{'macOS Version:':<{col}} {platform.mac_ver()[0]}")
        self.logger.info("=" * width)

    # ==========================================================================
    # Plugin lifecycle
    # ==========================================================================

    def startup(self):
        indigo.zwave.subscribeToIncoming()   # receive ALL Z-Wave bytes, including nodes with native Indigo devices
        self._rebuild_node_map()
        nodes = sorted(self.node_to_device.keys())
        self.logger.info(f"  Monitoring {len(nodes)} node(s): {nodes}")
        if self.debug:
            self.logger.debug("  Debug logging ENABLED")

    def shutdown(self):
        self.logger.info("Universal Z-Wave Sensor plugin stopping")

    def runConcurrentThread(self):
        """60-second tick — checks all plugin devices for stale (silent) condition."""
        try:
            while True:
                self._check_stale_devices()
                self.sleep(60)
        except self.StopThread:
            pass

    def closedPrefsConfigUi(self, values_dict, user_cancelled):
        if not user_cancelled:
            self.debug         = values_dict.get("showDebugInfo",        False)
            self.log_unknown   = values_dict.get("logUnknownReports",    True)
            self.temp_unit     = values_dict.get("tempUnit",             "degC")
            self.stale_enabled = values_dict.get("enableStaleDetection", True)
            self.stale_hours   = int(values_dict.get("staleThresholdHours", 24))
            self.logger.info(
                f"Prefs updated: debug={self.debug} log_unknown={self.log_unknown} "
                f"temp_unit={self.temp_unit} stale={self.stale_enabled}/{self.stale_hours}h"
            )

    # ==========================================================================
    # Device lifecycle
    # ==========================================================================

    def _sensor_type(self, device) -> str:
        """Return the sensor type string for a device.
        New typed devices (v5.1+) use deviceTypeId; legacy zwaveSensor reads pluginProps."""
        if device.deviceTypeId in DEVICE_TYPE_SENSOR_TYPE:
            return DEVICE_TYPE_SENSOR_TYPE[device.deviceTypeId]
        return device.pluginProps.get("sensorType", "generic")

    def _safe_update(self, device, state_id, **kwargs):
        """Update a device state only if that state exists on the device type.
        Silently skips states not in the device's state list — allows handlers to
        fan out to states that only exist on specific device types."""
        if state_id in device.states:
            device.updateStateOnServer(state_id, **kwargs)

    def _init_display_status(self, device):
        """Set displayStatus from existing state values at startup / reload.

        Prevents stale displayStatus after a plugin reload — e.g. a Temperature
        device that was incorrectly showing "detected" because a motion event
        set it before v3.5 fixed the displayStatus guards.
        """
        dev_type = self._sensor_type(device)
        states   = device.states

        if dev_type == "temperature":
            val = states.get("temperature")
            if val not in (None, ""):
                unit = self.temp_unit
                device.updateStateOnServer("displayStatus", value=f"{val} {unit}")

        elif dev_type == "humidity":
            val = states.get("humidity")
            if val not in (None, ""):
                device.updateStateOnServer("displayStatus", value=f"{val} %")

        elif dev_type == "luminance":
            val = states.get("luminance")
            if val not in (None, ""):
                device.updateStateOnServer("displayStatus", value=f"{val} lux")

        elif dev_type == "motion":
            motion = states.get("motion")
            if motion is not None:
                device.updateStateOnServer(
                    "displayStatus", value="detected" if motion else "clear"
                )

        elif dev_type == "contact":
            contact = states.get("contact")
            if contact is not None:
                device.updateStateOnServer(
                    "displayStatus", value="open" if contact else "closed"
                )

        elif dev_type == "energy":
            watts = states.get("watts")
            if watts not in (None, ""):
                device.updateStateOnServer("displayStatus", value=f"{watts} W")

        elif dev_type == "battery":
            val = states.get("batteryLevel")
            if val is not None:
                low = states.get("batteryLow", False)
                device.updateStateOnServer("displayStatus", value="LOW" if low else f"{val}%")

        elif dev_type == "lock":
            locked = states.get("lockState")
            if locked is not None:
                device.updateStateOnServer(
                    "displayStatus", value="locked" if locked else "unlocked"
                )

        elif dev_type == "scene":
            scene = states.get("lastScene")
            if scene is not None:
                action = states.get("lastSceneAction", "")
                device.updateStateOnServer(
                    "displayStatus", value=f"S{scene} {action}".strip()
                )

        # generic: leave displayStatus as-is (onOffState drives it at runtime)

    def deviceStartComm(self, device):
        if device.id in self._devices_starting:
            return
        self._devices_starting.add(device.id)
        try:
            self.logger.info(f"Starting: '{device.name}'")
            device.stateListOrDisplayStateIdChanged()
            self._init_display_status(device)
            node_id = self._get_node_id(device)
            if node_id:
                if node_id not in self.node_to_device:
                    self.node_to_device[node_id] = []
                if device.id not in self.node_to_device[node_id]:
                    self.node_to_device[node_id].append(device.id)
                self.logger.info(f"  Now listening on Z-Wave Node {node_id}")
            else:
                self.logger.error(
                    f"  No valid Node ID configured for '{device.name}' — edit device and set it"
                )
        finally:
            self._devices_starting.discard(device.id)

    def deviceStopComm(self, device):
        node_id = self._get_node_id(device)
        if node_id and node_id in self.node_to_device:
            try:
                self.node_to_device[node_id].remove(device.id)
            except ValueError:
                pass
            if not self.node_to_device[node_id]:
                del self.node_to_device[node_id]
            self.logger.info(f"Stopped listening on Node {node_id}")

    def validateDeviceConfigUi(self, values_dict, type_id, device_id):
        errors = indigo.Dict()

        # Read node ID from the selected native Indigo Z-Wave device
        native_id_str = values_dict.get("sourceDeviceId", "").strip()
        if not native_id_str or native_id_str == "none":
            errors["sourceDeviceId"] = "Select the native Indigo Z-Wave device for this sensor"
        else:
            try:
                native_dev = indigo.devices[int(native_id_str)]
                node_str   = str(native_dev.ownerProps.get("address", "")).strip()
                if not node_str.isdigit() or not (1 <= int(node_str) <= 232):
                    errors["sourceDeviceId"] = (
                        f"Could not read a valid Z-Wave node ID from '{native_dev.name}' "
                        f"(address='{node_str}')"
                    )
                else:
                    values_dict["nodeId"]  = node_str
                    values_dict["address"] = node_str
                    self.logger.info(
                        f"Device configured: node {node_str} from '{native_dev.name}'"
                    )
            except (KeyError, ValueError) as e:
                errors["sourceDeviceId"] = f"Could not read node ID from selected device: {e}"

        # Validate optional endpoint ID
        ep_str = values_dict.get("endpointId", "").strip()
        if ep_str and (not ep_str.isdigit() or not (0 <= int(ep_str) <= 255)):
            errors["endpointId"] = "Endpoint must be blank (all endpoints) or a number 0-255"

        return (len(errors) == 0), values_dict, errors

    def get_native_zwave_devices(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        ConfigUI callback — returns all non-plugin Indigo Z-Wave devices for the parallel mode picker.
        Only includes devices with a numeric address (Z-Wave node ID).
        """
        result = []
        for dev in indigo.devices:
            if dev.pluginId == self.pluginId:
                continue   # skip our own plugin devices
            node_str = str(getattr(dev, "address", "")).strip()
            if node_str.isdigit() and 1 <= int(node_str) <= 232:
                result.append((str(dev.id), f"{dev.name}  (Node {node_str})"))
        result.sort(key=lambda x: x[1])
        return result if result else [("none", "-- No native Z-Wave devices found --")]

    # ==========================================================================
    # Z-Wave report handler — receives ALL Z-Wave commands via subscribeToIncoming()
    # NOTE: Fires for ALL nodes, including those with native Indigo devices.
    #       Filtered below to only route to our registered plugin devices.
    # ==========================================================================

    def zwaveCommandReceived(self, cmd):
        """
        Called by Indigo for every incoming Z-Wave command directed at the
        controller. Receives reports from ALL nodes — we filter to our own.

        A single node can back multiple plugin devices (motion, temp, lux...);
        we iterate over all of them and route the report to each.
        """
        if self.debug:
            self.logger.debug(f"zwaveCommandReceived raw cmd: {dict(cmd)}")

        node_id, raw = self._extract_node_and_bytes(cmd)

        if node_id is None or len(raw) < 2:
            return

        if node_id not in self.node_to_device:
            return   # not one of our monitored nodes

        cmd_class = raw[0]
        cmd_func  = raw[1]
        hex_str   = " ".join(f"{b:02X}" for b in raw)

        for device_id in self.node_to_device[node_id]:
            try:
                device = indigo.devices[device_id]
            except KeyError:
                self.logger.error(
                    f"Node {node_id} mapped to device_id {device_id} but device not found"
                )
                continue

            if self.debug:
                self.logger.debug(
                    f"{device.name} [Node {node_id}]: "
                    f"CC=0x{cmd_class:02X} func=0x{cmd_func:02X} [{hex_str}]"
                )

            self._route_zwave_report(device, node_id, cmd_class, cmd_func, raw, hex_str)

    def _route_zwave_report(self, device, node_id, cmd_class, cmd_func, raw, hex_str):
        """Dispatch one Z-Wave report to the correct parser for a single plugin device."""

        # ------------------------------------------------------------------
        # Multi-channel encapsulation (CC 0x60, CMD 0x0D)
        # Frame: [0x60, 0x0D, src_endpoint, dst_endpoint, cc, func, payload...]
        # Unwrap the inner frame, then optionally filter by endpoint.
        # ------------------------------------------------------------------
        if cmd_class == CC_MULTI_CHANNEL and cmd_func == CMD_MULTI_CHANNEL_ENCAP:
            if len(raw) < 6:
                return
            src_ep    = raw[2]
            dst_ep    = raw[3]
            raw       = raw[4:]            # inner frame: [cc, func, payload...]
            cmd_class = raw[0]
            cmd_func  = raw[1]
            hex_str   = " ".join(f"{b:02X}" for b in raw)

            # Per-device endpoint filter — blank or "0" means accept all endpoints
            ep_str = device.pluginProps.get("endpointId", "").strip()
            if ep_str and ep_str != "0":
                try:
                    if dst_ep != int(ep_str):
                        if self.debug:
                            self.logger.debug(
                                f"{device.name}: MC dst_ep={dst_ep} "
                                f"(want ep {ep_str}) — skipped"
                            )
                        return
                except ValueError:
                    pass

            if self.debug:
                self.logger.debug(
                    f"{device.name}: Multi-channel src_ep={src_ep} dst_ep={dst_ep} "
                    f"-> CC=0x{cmd_class:02X} [{hex_str}]"
                )

        # ------------------------------------------------------------------
        # Dispatch to parser
        # ------------------------------------------------------------------
        handled = False

        if   cmd_class == CC_SENSOR_MULTILEVEL  and cmd_func == CMD_SENSOR_MULTILEVEL_REPORT:
            handled = self._handle_multilevel(device, raw)

        elif cmd_class == CC_SENSOR_BINARY      and cmd_func == CMD_SENSOR_BINARY_REPORT:
            handled = self._handle_binary_sensor(device, raw)

        elif cmd_class == CC_NOTIFICATION       and cmd_func == CMD_NOTIFICATION_REPORT:
            handled = self._handle_notification(device, raw)

        elif cmd_class == CC_BATTERY            and cmd_func == CMD_BATTERY_REPORT:
            handled = self._handle_battery(device, raw)

        elif cmd_class == CC_METER              and cmd_func == CMD_METER_REPORT:
            handled = self._handle_meter(device, raw)

        elif cmd_class == CC_SWITCH_BINARY      and cmd_func == CMD_SWITCH_BINARY_REPORT:
            handled = self._handle_switch_binary(device, raw)

        elif cmd_class == CC_SWITCH_MULTILEVEL  and cmd_func == CMD_SWITCH_MULTILEVEL_REPORT:
            handled = self._handle_switch_multilevel(device, raw)

        elif cmd_class == CC_BASIC              and cmd_func == CMD_BASIC_REPORT:
            handled = self._handle_basic(device, raw)

        elif cmd_class == CC_CENTRAL_SCENE     and cmd_func == CMD_CENTRAL_SCENE_NOTIFICATION:
            handled = self._handle_central_scene(device, raw)

        elif cmd_class == CC_DOOR_LOCK         and cmd_func == CMD_DOOR_LOCK_REPORT:
            handled = self._handle_door_lock(device, raw)

        elif cmd_class == CC_WAKE_UP:
            handled = self._handle_wake_up(device, cmd_func, raw)

        if not handled and self.log_unknown:
            self.logger.info(
                f"{device.name} [Node {node_id}]: "
                f"Unhandled CC=0x{cmd_class:02X} func=0x{cmd_func:02X} [{hex_str}]"
            )
            device.updateStateOnServer("rawLastReport", value=hex_str)

    # ==========================================================================
    # Report parsers
    # ==========================================================================

    def _handle_multilevel(self, device, raw) -> bool:
        """
        SENSOR_MULTILEVEL_REPORT (CC=0x31, cmd=0x05)
        Byte layout:
          [0x31, 0x05, sensor_type, prec_scale_size, value_bytes...]
          prec_scale_size:  bits [7:5]=precision  [4:3]=scale  [2:0]=size
          value_bytes:      signed big-endian, 1/2/4 bytes
          actual_value = raw_int / 10^precision
        Temperature is converted to the user's preferred unit (degC/degF).
        """
        if len(raw) < 5:
            return False

        sensor_type     = raw[2]
        prec_scale_size = raw[3]
        size            = prec_scale_size & 0x07
        scale           = (prec_scale_size >> 3) & 0x03
        precision       = (prec_scale_size >> 5) & 0x07

        if len(raw) < 4 + size:
            return False

        value_bytes = raw[4:4 + size]
        try:
            if   size == 1: raw_val = struct.unpack(">b", bytes(value_bytes))[0]
            elif size == 2: raw_val = struct.unpack(">h", bytes(value_bytes))[0]
            elif size == 4: raw_val = struct.unpack(">i", bytes(value_bytes))[0]
            else:           return False
        except struct.error as e:
            self.logger.error(f"{device.name}: SENSOR_MULTILEVEL parse error: {e}")
            return False

        value = raw_val / (10 ** precision)

        if sensor_type not in SENSOR_TYPES:
            self.logger.info(
                f"{device.name}: Unknown sensor type 0x{sensor_type:02X} "
                f"value={value} scale={scale} — add to SENSOR_TYPES to handle"
            )
            return False

        state_key, default_unit = SENSOR_TYPES[sensor_type]

        # Resolve unit; apply temperature unit preference with conversion if needed
        if sensor_type == 0x01:   # temperature
            reported_unit = "degC" if scale == 0 else "degF"
            if reported_unit != self.temp_unit:
                if self.temp_unit == "degF":
                    value = value * 9.0 / 5.0 + 32.0
                else:   # degC
                    value = (value - 32.0) * 5.0 / 9.0
                precision = max(precision, 1)   # ensure at least 1dp after conversion
            unit = self.temp_unit
        elif sensor_type == 0x03:  # luminance
            unit = "%" if scale == 0 else "lux"
        else:
            unit = default_unit

        dp     = max(0, precision)
        ui_str = f"{value:.{dp}f} {unit}".strip()

        # Only log at INFO when this report matches the device's primary sensor type;
        # secondary values (e.g. temperature on a Lux device) log at DEBUG only.
        dev_sensor_type = self._sensor_type(device)
        _log = self.logger.info if dev_sensor_type == state_key else self.logger.debug
        _log(f"{device.name}: {state_key} = {ui_str}")
        self._safe_update(device, state_key, value=round(value, dp), uiValue=ui_str)

        if dev_sensor_type == state_key:
            device.updateStateOnServer("displayStatus", value=ui_str)
            _zw_icon_map = {
                "temperature": indigo.kStateImageSel.TemperatureSensor,
                "humidity":    indigo.kStateImageSel.HumiditySensor,
                "luminance":   indigo.kStateImageSel.LightSensor,
            }
            device.updateStateImageOnServer(
                _zw_icon_map.get(state_key, indigo.kStateImageSel.SensorOn)
            )

        self._touch(device)
        return True

    def _handle_binary_sensor(self, device, raw) -> bool:
        """
        SENSOR_BINARY_REPORT (CC=0x30, cmd=0x03)
        v1: [0x30, 0x03, value]
        v2: [0x30, 0x03, value, sensor_type]
        value: 0xFF=active/triggered  0x00=idle/clear
        """
        if len(raw) < 3:
            return False

        is_active   = (raw[2] == 0xFF)
        sensor_type = raw[3] if len(raw) >= 4 else 0x01
        state_key   = BINARY_SENSOR_TYPES.get(sensor_type, "onOffState")

        labels = {
            "contact":   ("open",     "closed"),
            "motion":    ("detected", "clear"),
            "waterLeak": ("leak",     "clear"),
            "smoke":     ("smoke",    "clear"),
            "coAlarm":   ("alarm",    "clear"),
            "tamper":    ("tamper",   "clear"),
        }
        on_label, off_label = labels.get(state_key, ("active", "idle"))
        label = on_label if is_active else off_label

        # SENSOR_BINARY is the older CC 0x30 format; sensors that also send NOTIFICATION
        # (CC 0x71) will produce a duplicate INFO line. Always log SENSOR_BINARY at DEBUG
        # to keep the event log clean — NOTIFICATION provides the primary INFO message.
        dev_type   = self._sensor_type(device)
        is_primary = (dev_type == "generic"
                      or (state_key == "motion"  and dev_type == "motion")
                      or (state_key == "contact" and dev_type == "contact"))
        self.logger.debug(f"{device.name}: {state_key} = {label}")
        self._safe_update(device, state_key,    value=is_active, uiValue=label)
        device.updateStateOnServer("onOffState", value=is_active)
        if is_primary:
            device.updateStateOnServer("displayStatus", value=label)
        self._touch(device)
        return True

    def _handle_notification(self, device, raw) -> bool:
        """
        NOTIFICATION_REPORT v4+ (CC=0x71, cmd=0x05)
        Z-Wave spec byte layout:
          [0x71, 0x05, v1_type, v1_level, reserved,
           notif_status (0xFF/0x00), notif_type, notif_event,
           event_params_len, event_params...]
        Some older devices reverse notif_status and notif_type.
        Auto-detected: notif_status is always 0x00 or 0xFF; notif_type is 0x01..0x1F.
        """
        if len(raw) < 8:
            return False

        # Auto-detect byte order: Status byte is only ever 0x00 or 0xFF
        if raw[5] in (0x00, 0xFF):
            notif_status = raw[5]   # spec order (standard hardware)
            notif_type   = raw[6]
        else:
            notif_type   = raw[5]   # reversed order (some older devices)
            notif_status = raw[6]
        notif_event  = raw[7]

        if notif_type == NOTIF_HOME_SECURITY:
            _dt           = self._sensor_type(device)
            _motion_disp  = _dt in ("motion", "generic")
            _log          = self.logger.info if _motion_disp else self.logger.debug
            if notif_event in (HS_MOTION_DETECTED, HS_MOTION_DETECTED_NL):
                _log(f"{device.name}: Motion DETECTED")
                self._safe_update(device, "motion",     value=True,  uiValue="detected")
                device.updateStateOnServer("onOffState", value=True)
                if _motion_disp:
                    device.updateStateOnServer("displayStatus", value="detected")
            elif notif_event in (HS_TAMPER, HS_TAMPER_ALT):
                _log(f"{device.name}: Tamper DETECTED")
                self._safe_update(device, "tamper",     value=True,  uiValue="tamper")
                if _motion_disp:
                    device.updateStateOnServer("displayStatus", value="tamper")
            elif notif_event in (HS_INTRUSION, HS_INTRUSION_NL):
                _log(f"{device.name}: Intrusion DETECTED")
                self._safe_update(device, "motion",     value=True,  uiValue="intrusion")
                device.updateStateOnServer("onOffState", value=True)
                if _motion_disp:
                    device.updateStateOnServer("displayStatus", value="intrusion")
            elif notif_event in (HS_GLASS_BREAK, HS_GLASS_BREAK_NL):
                _log(f"{device.name}: Glass break DETECTED")
                self._safe_update(device, "motion",     value=True,  uiValue="glass break")
                device.updateStateOnServer("onOffState", value=True)
                if _motion_disp:
                    device.updateStateOnServer("displayStatus", value="glass break")
            elif notif_event == HS_IDLE:
                self.logger.debug(f"{device.name}: Home security idle (all clear)")
                self._safe_update(device, "motion",     value=False, uiValue="clear")
                self._safe_update(device, "tamper",     value=False, uiValue="clear")
                device.updateStateOnServer("onOffState", value=False)
                if _motion_disp:
                    device.updateStateOnServer("displayStatus", value="clear")
            else:
                self.logger.info(
                    f"{device.name}: HOME_SECURITY event=0x{notif_event:02X} "
                    f"status=0x{notif_status:02X} (unhandled)"
                )
            self._touch(device)
            return True

        elif notif_type == NOTIF_ACCESS_CONTROL:
            _dt            = self._sensor_type(device)
            _contact_disp  = _dt in ("contact", "generic")
            _lock_disp     = _dt in ("lock", "generic")
            _log_c         = self.logger.info if _contact_disp else self.logger.debug
            _log_l         = self.logger.info if _lock_disp    else self.logger.debug
            if notif_event == AC_DOOR_OPEN:
                _log_c(f"{device.name}: Door/Window OPEN")
                self._safe_update(device, "contact",    value=True,  uiValue="open")
                device.updateStateOnServer("onOffState", value=True)
                if _contact_disp:
                    device.updateStateOnServer("displayStatus", value="open")
            elif notif_event == AC_DOOR_CLOSED:
                _log_c(f"{device.name}: Door/Window CLOSED")
                self._safe_update(device, "contact",    value=False, uiValue="closed")
                device.updateStateOnServer("onOffState", value=False)
                if _contact_disp:
                    device.updateStateOnServer("displayStatus", value="closed")
            elif notif_event in (AC_MANUAL_LOCK, AC_RF_LOCK, AC_KEYPAD_LOCK, AC_AUTO_LOCK):
                user_id = self._extract_notif_user(raw)
                user_str = f" user={user_id}" if user_id else ""
                _log_l(f"{device.name}: Lock LOCKED (event=0x{notif_event:02X}){user_str}")
                self._safe_update(device, "lockState",  value=True,  uiValue="locked")
                device.updateStateOnServer("onOffState", value=True)
                if user_id is not None:
                    self._safe_update(device, "lastUser", value=user_id)
                if _lock_disp:
                    device.updateStateOnServer("displayStatus", value="locked")
            elif notif_event in (AC_MANUAL_UNLOCK, AC_RF_UNLOCK, AC_KEYPAD_UNLOCK):
                user_id = self._extract_notif_user(raw)
                user_str = f" user={user_id}" if user_id else ""
                _log_l(f"{device.name}: Lock UNLOCKED (event=0x{notif_event:02X}){user_str}")
                self._safe_update(device, "lockState",  value=False, uiValue="unlocked")
                device.updateStateOnServer("onOffState", value=False)
                if user_id is not None:
                    self._safe_update(device, "lastUser", value=user_id)
                if _lock_disp:
                    device.updateStateOnServer("displayStatus", value="unlocked")
            elif notif_event == AC_LOCK_JAMMED:
                self.logger.warning(f"{device.name}: Lock JAMMED")
                if _lock_disp:
                    device.updateStateOnServer("displayStatus", value="jammed")
            else:
                self.logger.info(
                    f"{device.name}: ACCESS_CONTROL event=0x{notif_event:02X} (unhandled)"
                )
            self._touch(device)
            return True

        elif notif_type == NOTIF_WATER:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: Water LEAK detected")
                self._safe_update(device, "waterLeak",     value=True,  uiValue="leak")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="leak")
            elif notif_event == 0x00 or notif_status == 0x00:
                self.logger.info(f"{device.name}: Water leak CLEARED")
                self._safe_update(device, "waterLeak",     value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            self._touch(device)
            return True

        elif notif_type == NOTIF_SMOKE:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: Smoke DETECTED")
                self._safe_update(device, "smoke",         value=True,  uiValue="smoke")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="smoke")
            elif notif_event == 0x00:
                self.logger.info(f"{device.name}: Smoke CLEARED")
                self._safe_update(device, "smoke",         value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            self._touch(device)
            return True

        elif notif_type == NOTIF_CO:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: CO ALARM")
                self._safe_update(device, "coAlarm",       value=True,  uiValue="alarm")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="alarm")
            elif notif_event == 0x00:
                self.logger.info(f"{device.name}: CO alarm CLEARED")
                self._safe_update(device, "coAlarm",       value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            self._touch(device)
            return True

        elif notif_type == NOTIF_POWER_MANAGEMENT:
            if notif_event in (PM_REPLACE_BATTERY, PM_REPLACE_BATTERY_NOW):
                urgency = "now" if notif_event == PM_REPLACE_BATTERY_NOW else "soon"
                self.logger.warning(f"{device.name}: Battery — replace {urgency}")
                device.updateStateOnServer("batteryLow", value=True)
            elif notif_event == PM_AC_DISCONNECTED:
                self.logger.warning(f"{device.name}: AC mains DISCONNECTED")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="AC off")
            elif notif_event == PM_AC_RECONNECTED:
                self.logger.info(f"{device.name}: AC mains RECONNECTED")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="AC on")
            elif notif_event == PM_OVER_CURRENT:
                self.logger.warning(f"{device.name}: Over-current DETECTED")
                device.updateStateOnServer("displayStatus", value="over-current")
            elif notif_event == PM_BATTERY_CHARGING:
                self.logger.info(f"{device.name}: Battery charging")
                device.updateStateOnServer("displayStatus", value="charging")
            elif notif_event == PM_BATTERY_CHARGED:
                self.logger.info(f"{device.name}: Battery fully charged")
                device.updateStateOnServer("displayStatus", value="charged")
            else:
                self.logger.info(
                    f"{device.name}: POWER_MANAGEMENT event=0x{notif_event:02X} "
                    f"status=0x{notif_status:02X} (unhandled)"
                )
            self._touch(device)
            return True

        # Unknown notification type — log for investigation
        self.logger.info(
            f"{device.name}: NOTIFICATION type=0x{notif_type:02X} "
            f"status=0x{notif_status:02X} event=0x{notif_event:02X} (unhandled)"
        )
        return False

    def _handle_battery(self, device, raw) -> bool:
        """
        BATTERY_REPORT (CC=0x80, cmd=0x03)
        [0x80, 0x03, level]
        level: 0-100 = battery %   0xFF = battery low warning from device
        batteryLow is set True when level is 0xFF sentinel or <= 20%.
        For sensorType=battery devices, displayStatus and onOffState are also updated.
        """
        if len(raw) < 3:
            return False

        raw_level = raw[2]
        if raw_level == 0xFF:
            level  = 1
            is_low = True
            ui_str = "LOW"
            self.logger.warning(f"{device.name}: Battery LOW warning received from device")
        else:
            level  = raw_level
            is_low = level <= 20
            ui_str = f"{level}%"
            self.logger.info(f"{device.name}: Battery = {level}%")

        device.updateStateOnServer("batteryLevel", value=level, uiValue=ui_str)
        device.updateStateOnServer("batteryLow",   value=is_low)

        dev_type = self._sensor_type(device)
        if dev_type == "battery":
            device.updateStateOnServer("displayStatus", value=ui_str)
            device.updateStateOnServer("onOffState",    value=not is_low)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorTripped if is_low
                else indigo.kStateImageSel.SensorOn
            )

        self._touch(device)
        return True

    def _handle_meter(self, device, raw) -> bool:
        """
        METER_REPORT v2/v3 (CC=0x32, cmd=0x02)
        Byte layout:
          [0x32, 0x02, meter_type_rate, prec_scale_size, value_bytes...]
          meter_type_rate: bit [7]=Scale2  bits [6:5]=rate_type  [4:0]=meter_type
          prec_scale_size: bits [7:5]=precision  [4:3]=scale_lsb  [2:0]=size
          v3 full scale (3-bit): Scale2 << 2 | scale_lsb
            0=kWh  1=kVAh  2=W  3=pulse  4=V  5=A
        """
        if len(raw) < 6:
            return False

        meter_type_rate = raw[2]
        prec_scale_size = raw[3]
        meter_type      = meter_type_rate & 0x1F
        size            = prec_scale_size & 0x07
        scale_lsb       = (prec_scale_size >> 3) & 0x03
        scale2_bit      = (meter_type_rate   >> 7) & 0x01   # v3 MSB of scale
        scale           = (scale2_bit << 2) | scale_lsb
        precision       = (prec_scale_size >> 5) & 0x07

        if len(raw) < 4 + size:
            return False

        value_bytes = raw[4:4 + size]
        try:
            if   size == 1: raw_val = struct.unpack(">b", bytes(value_bytes))[0]
            elif size == 2: raw_val = struct.unpack(">h", bytes(value_bytes))[0]
            elif size == 4: raw_val = struct.unpack(">i", bytes(value_bytes))[0]
            else:           return False
        except struct.error as e:
            self.logger.error(f"{device.name}: METER parse error: {e}")
            return False

        value = raw_val / (10 ** precision)

        if meter_type == METER_ELECTRIC:
            scale_info = METER_ELECTRIC_SCALES.get(scale)
            if scale_info:
                state_key, unit = scale_info
                ui_str = f"{value:.3f} {unit}"
                self.logger.info(f"{device.name}: {state_key} = {ui_str}")
                self._safe_update(device, state_key,       value=round(value, 3), uiValue=ui_str)
                device.updateStateOnServer("displayStatus", value=ui_str)
                self._touch(device)
                return True

        elif meter_type == METER_GAS:
            scale_info = METER_GAS_SCALES.get(scale)
            if scale_info:
                state_key, unit = scale_info
                ui_str = f"{value:.3f} {unit}"
                self.logger.info(f"{device.name}: gas = {ui_str}")
                self._safe_update(device, state_key,       value=round(value, 3), uiValue=ui_str)
                device.updateStateOnServer("displayStatus", value=ui_str)
                self._touch(device)
                return True

        elif meter_type == METER_WATER:
            scale_info = METER_WATER_SCALES.get(scale)
            if scale_info:
                state_key, unit = scale_info
                ui_str = f"{value:.3f} {unit}"
                self.logger.info(f"{device.name}: water = {ui_str}")
                self._safe_update(device, state_key,       value=round(value, 3), uiValue=ui_str)
                device.updateStateOnServer("displayStatus", value=ui_str)
                self._touch(device)
                return True

        self.logger.info(
            f"{device.name}: METER type=0x{meter_type:02X} scale={scale} "
            f"value={value} (unhandled meter type or scale)"
        )
        return False

    def _handle_switch_binary(self, device, raw) -> bool:
        """
        SWITCH_BINARY_REPORT (CC=0x25, cmd=0x03)
        v1: [0x25, 0x03, value]
        v2: [0x25, 0x03, value, target_value, duration]
        value: 0x00=off  0xFF=on
        """
        if len(raw) < 3:
            return False

        is_on = (raw[2] != 0x00)
        label = "on" if is_on else "off"
        self.logger.info(f"{device.name}: Switch = {label}")
        self._safe_update(device, "switchState",   value=is_on, uiValue=label)
        device.updateStateOnServer("onOffState",    value=is_on)
        device.updateStateOnServer("displayStatus", value=label)
        self._touch(device)
        return True

    def _handle_switch_multilevel(self, device, raw) -> bool:
        """
        SWITCH_MULTILEVEL_REPORT (CC=0x26, cmd=0x03)
        [0x26, 0x03, value]
        value: 0-99=dim level  0xFF=restore last non-zero level
        """
        if len(raw) < 3:
            return False

        raw_val     = raw[2]
        level       = 99 if raw_val == 0xFF else min(raw_val, 99)
        is_on       = level > 0
        display_str = f"{level}%" if is_on else "off"
        self.logger.info(f"{device.name}: Dim level = {level}%")
        self._safe_update(device, "dimLevel",      value=level, uiValue=f"{level}%")
        self._safe_update(device, "switchState",   value=is_on)
        device.updateStateOnServer("onOffState",    value=is_on)
        device.updateStateOnServer("displayStatus", value=display_str)
        self._touch(device)
        return True

    def _handle_basic(self, device, raw) -> bool:
        """
        BASIC_REPORT (CC=0x20, cmd=0x03)
        [0x20, 0x03, value]
        value: 0=off  1-99=on/dim  0xFF=on (full)
        Legacy command class used by many older devices as a catch-all.
        """
        if len(raw) < 3:
            return False

        raw_val = raw[2]
        level   = 99 if raw_val == 0xFF else raw_val
        is_on   = level > 0
        self.logger.info(f"{device.name}: Basic report = {level}")
        self._safe_update(device, "dimLevel",   value=level, uiValue=str(level))
        device.updateStateOnServer("onOffState", value=is_on)
        self._touch(device)
        return True

    def _handle_wake_up(self, device, cmd_func, raw) -> bool:
        """
        WAKE_UP command class (CC=0x84)
        CMD 0x07  WAKE_UP_NOTIFICATION      [0x84, 0x07]
                  Device woke up and is ready to receive queued commands.
        CMD 0x06  WAKE_UP_INTERVAL_REPORT   [0x84, 0x06, b1, b2, b3, node_id]
                  interval_s = (b1 << 16) | (b2 << 8) | b3
        """
        if cmd_func == CMD_WAKE_UP_NOTIFICATION:
            self.logger.debug(f"{device.name}: Wake-up notification (device is awake)")
            self._touch(device)
            return True

        if cmd_func == CMD_WAKE_UP_INTERVAL_REPORT:
            if len(raw) < 5:
                return False
            interval = (raw[2] << 16) | (raw[3] << 8) | raw[4]
            minutes  = interval // 60
            seconds  = interval % 60
            ui_str   = f"{minutes}m {seconds}s" if minutes else f"{interval}s"
            self.logger.info(f"{device.name}: Wake-up interval = {interval}s ({ui_str})")
            device.updateStateOnServer("wakeUpInterval", value=interval, uiValue=ui_str)
            self._touch(device)
            return True

        return False

    def _handle_central_scene(self, device, raw) -> bool:
        """
        CENTRAL_SCENE_NOTIFICATION (CC=0x5B, cmd=0x03)
        v1/v2: [0x5B, 0x03, seq_no, key_attributes, scene_number]
        key_attributes bits [2:0]: action (0=pressed, 1=released, 2=held, 3=double, ...)
        bit 7 of key_attributes = slow_refresh flag (ignore for our purposes)
        Fires whenever a button on a scene controller (WallMote, remote, etc.) is used.
        """
        if len(raw) < 5:
            return False

        seq_no        = raw[2]
        key_attr_byte = raw[3]
        scene_number  = raw[4]
        action_code   = key_attr_byte & 0x07   # strip slow_refresh bit

        action_str = CENTRAL_SCENE_KEY_ACTIONS.get(action_code, f"action_{action_code}")
        ts         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        disp_str   = f"S{scene_number} {action_str}"

        self.logger.info(
            f"{device.name}: Scene {scene_number} — {action_str} (seq={seq_no})"
        )
        self._safe_update(device, "lastScene",       value=scene_number)
        self._safe_update(device, "lastSceneAction", value=action_str)
        self._safe_update(device, "sceneTimestamp",  value=ts)
        device.updateStateOnServer("displayStatus",   value=disp_str)
        # onOffState: True on press/held/double, False on release
        device.updateStateOnServer("onOffState",      value=(action_code != CS_KEY_RELEASED))
        self._touch(device)
        return True

    def _handle_door_lock(self, device, raw) -> bool:
        """
        DOOR_LOCK_OPERATION_REPORT (CC=0x62, cmd=0x03)
        v1:  [0x62, 0x03, mode]
        v2+: [0x62, 0x03, mode, handles_mode, door_condition, timeout_min, timeout_sec]
        mode: 0x00=unsecured  0x01=unsecured+timeout  0x10=inside-handle  0xFF=secured

        door_condition byte (raw[4], v2+ only):
          bit 0 SET = door physically open
          bit 1 SET = bolt unlocked  (0 = bolt locked / deadbolt extended)
          bit 2 SET = latch open     (0 = latch closed / latched)
        """
        if len(raw) < 3:
            return False

        mode      = raw[2]
        is_locked = (mode == 0xFF)
        label     = "locked" if is_locked else "unlocked"

        self.logger.info(f"{device.name}: Lock {label} (mode=0x{mode:02X})")
        self._safe_update(device, "lockState",     value=is_locked, uiValue=label)
        self._safe_update(device, "lockMode",      value=mode)
        device.updateStateOnServer("onOffState",    value=is_locked)
        device.updateStateOnServer("displayStatus", value=label)
        device.updateStateImageOnServer(
            indigo.kStateImageSel.SensorTripped if is_locked
            else indigo.kStateImageSel.SensorOff
        )

        # v2+ door condition bitmask
        if len(raw) >= 5:
            door_condition = raw[4]
            bolt_locked    = not bool((door_condition >> 1) & 0x01)
            latch_closed   = not bool((door_condition >> 2) & 0x01)
            self.logger.debug(
                f"{device.name}: door_condition=0x{door_condition:02X} "
                f"bolt={'locked' if bolt_locked else 'unlocked'} "
                f"latch={'closed' if latch_closed else 'open'}"
            )
            self._safe_update(
                device, "boltState",  value=bolt_locked,
                uiValue="locked" if bolt_locked else "unlocked"
            )
            self._safe_update(
                device, "latchState", value=latch_closed,
                uiValue="closed" if latch_closed else "open"
            )

        self._touch(device)
        return True

    # ==========================================================================
    # Stale device detection
    # ==========================================================================

    def _check_stale_devices(self):
        """
        Called every 60 seconds by runConcurrentThread.
        A device is stale if lastUpdate is older than stale_hours.
        Logs a warning the first time each device goes stale and sets
        deviceOnline=False.  _touch() clears the stale flag and restores
        deviceOnline=True when any report arrives.
        """
        if not self.stale_enabled:
            return

        threshold = timedelta(hours=self.stale_hours)
        now       = datetime.now()

        for dev in indigo.devices.iter("self"):
            last_str = dev.states.get("lastUpdate", "")
            if not last_str:
                continue   # never had a report — cannot determine staleness

            try:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            age      = now - last_dt
            is_stale = age > threshold

            if is_stale and dev.id not in self.stale_device_ids:
                # Newly stale — log once and mark offline
                self.stale_device_ids.add(dev.id)
                hours_ago = age.total_seconds() / 3600
                self.logger.warning(
                    f"{dev.name}: No report for {hours_ago:.1f}h "
                    f"(threshold {self.stale_hours}h) — may be offline or out of range"
                )
                dev.updateStateOnServer("deviceOnline", value=False, uiValue="offline")

            elif not is_stale and dev.id in self.stale_device_ids:
                # Threshold was raised while device was flagged — clear without logging
                self.stale_device_ids.discard(dev.id)
                dev.updateStateOnServer("deviceOnline", value=True, uiValue="online")

    # ==========================================================================
    # Menu: Simulate Z-Wave Report
    # ==========================================================================

    def get_sim_device_list(self, filter="", values_dict=None, type_id="", target_id=0):
        """ConfigUI callback — returns all plugin devices for the simulate dialog."""
        result = []
        for dev in indigo.devices.iter("self"):
            node_id = self._get_node_id(dev)
            if node_id:
                result.append((str(dev.id), f"{dev.name}  (Node {node_id})"))
        return result if result else [("none", "-- No plugin devices configured --")]

    def simulateReport(self, values_dict, type_id):
        """
        Menu: Simulate Z-Wave Report
        Feeds user-supplied hex bytes directly into _route_zwave_report() for
        the selected plugin device, exactly as if real hardware had sent them.
        Returns values_dict to keep the dialog open for further testing.

        Example byte sequences:
          Temperature 21.5 degC:      31 05 01 22 00 D7
          Humidity 35.1%:             31 05 05 22 01 5F
          Motion detected (NOTIF):    71 05 00 00 00 FF 07 07 00
          Motion cleared  (NOTIF):    71 05 00 00 00 FF 07 08 00
          Door open       (NOTIF):    71 05 00 00 00 FF 06 16 00
          Door closed     (NOTIF):    71 05 00 00 00 FF 06 17 00
          Lock locked     (CC 0x62):  62 03 FF
          Lock unlocked   (CC 0x62):  62 03 00
          Scene 1 pressed (WallMote): 5B 03 01 00 01
          Scene 2 double  (WallMote): 5B 03 02 03 02
          Battery 85%:                80 03 55
          Battery LOW sentinel:       80 03 FF
          Wake-up interval 5min:      84 06 00 01 2C 6F
          Wake-up notification:       84 07
        """
        try:
            dev_id_str = str(values_dict.get("deviceId", "")).strip()
            hex_input  = str(values_dict.get("hexBytes",  "")).strip()

            if not dev_id_str or dev_id_str == "none" or not hex_input:
                self.logger.error("Simulate: select a device and enter hex bytes")
                return values_dict

            try:
                device = indigo.devices[int(dev_id_str)]
            except (KeyError, ValueError):
                self.logger.error(f"Simulate: device id '{dev_id_str}' not found")
                return values_dict

            node_id = self._get_node_id(device)
            if not node_id:
                self.logger.error("Simulate: device has no valid node ID")
                return values_dict

            try:
                raw = [int(b, 16) for b in hex_input.split()]
            except ValueError as e:
                self.logger.error(
                    f"Simulate: invalid hex — {e}  "
                    f"(expected space-separated bytes, e.g. 31 05 01 22 00 D7)"
                )
                return values_dict

            if len(raw) < 2:
                self.logger.error("Simulate: need at least 2 bytes (command class + command)")
                return values_dict

            cmd_class = raw[0]
            cmd_func  = raw[1]
            hex_str   = " ".join(f"{b:02X}" for b in raw)

            self.logger.info(
                f"Simulate: -> '{device.name}' [Node {node_id}] "
                f"CC=0x{cmd_class:02X} func=0x{cmd_func:02X} [{hex_str}]"
            )
            self._route_zwave_report(device, node_id, cmd_class, cmd_func, raw, hex_str)

        except Exception as e:
            self.logger.error(f"Simulate: unexpected error — {e}", exc_info=True)

        return values_dict   # keeps the dialog open for further testing

    # ==========================================================================
    # Helpers
    # ==========================================================================

    def _extract_node_and_bytes(self, cmd) -> tuple[int | None, list[int]]:
        """
        Extract node_id and raw Z-Wave command bytes from cmd dict.

        When subscribeToIncoming() is active, Indigo delivers the full Z-Wave
        serial API frame rather than just the command payload.
        APPLICATION_COMMAND_HANDLER frames are detected and unwrapped:
          [01, LEN, 00, 04, rxStatus, srcNode, cmdLen, cmd_bytes..., checksum]
           ^SOF         ^FUNC=0x04    ^node    ^len    ^-- actual Z-Wave here

        For plugin-owned devices (without subscribeToIncoming), the bytes field
        already contains just the command payload — no unwrapping needed.
        """
        node_id = cmd.get("nodeId",
                  cmd.get("sourceNodeId",
                  cmd.get("node_id", None)))

        raw = list(cmd.get("bytes",
               cmd.get("cmdBytes",
               cmd.get("rawBytes", []))))

        # Detect and unwrap Z-Wave serial API frame.
        # SOF=0x01 at byte 0, FUNC_ID_APPLICATION_COMMAND_HANDLER=0x04 at byte 3.
        # No valid Z-Wave command class uses 0x01, so this detection is safe.
        if len(raw) >= 8 and raw[0] == 0x01 and raw[3] == 0x04:
            cmd_len = raw[6]
            if len(raw) >= 7 + cmd_len:
                raw = raw[7:7 + cmd_len]

        return node_id, raw

    def _update_display(self, device, sensor_type: str, is_on: bool):
        """Set displayStatus string and device icon based on configured sensor type."""
        if sensor_type == "motion":
            label = "detected" if is_on else "clear"
            device.updateStateOnServer("displayStatus", value=label)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.MotionSensorTripped if is_on
                else indigo.kStateImageSel.MotionSensor
            )
        elif sensor_type == "contact":
            label = "open" if is_on else "closed"
            device.updateStateOnServer("displayStatus", value=label)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorTripped if is_on
                else indigo.kStateImageSel.SensorOff
            )
        elif sensor_type == "luminance":
            device.updateStateImageOnServer(
                indigo.kStateImageSel.LightSensorOn if is_on
                else indigo.kStateImageSel.LightSensor
            )
        elif sensor_type == "temperature":
            device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensor)
        elif sensor_type == "humidity":
            device.updateStateImageOnServer(indigo.kStateImageSel.HumiditySensor)
        elif sensor_type == "energy":
            device.updateStateImageOnServer(
                indigo.kStateImageSel.PowerOn if is_on
                else indigo.kStateImageSel.PowerOff
            )
        elif sensor_type == "battery":
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorTripped if not is_on
                else indigo.kStateImageSel.SensorOn
            )
        elif sensor_type == "lock":
            label = "locked" if is_on else "unlocked"
            device.updateStateOnServer("displayStatus", value=label)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorTripped if is_on
                else indigo.kStateImageSel.SensorOff
            )
        elif sensor_type == "scene":
            device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
        else:   # generic
            label = "on" if is_on else "off"
            device.updateStateOnServer("displayStatus", value=label)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorOn if is_on
                else indigo.kStateImageSel.SensorOff
            )

    def _extract_notif_user(self, raw) -> int | None:
        """
        Extract user slot ID from a NOTIFICATION_REPORT event params field.
        Frame layout: [..., notif_event, event_params_len, event_param_1, ...]
        raw[7]=event, raw[8]=params_len, raw[9]=user_id (if params_len >= 1).
        Returns None if no event params are present.
        User 0 = no user / unknown; 251 = master code; 1-250 = regular slots.
        """
        if len(raw) >= 10 and raw[8] >= 1:
            user_id = raw[9]
            return user_id if user_id > 0 else None
        return None

    def _get_node_id(self, device) -> int | None:
        node_str = device.pluginProps.get("nodeId", "").strip()
        return int(node_str) if node_str.isdigit() else None

    def _rebuild_node_map(self):
        """Rebuild node_id -> [device_id, ...] map from all plugin devices."""
        self.node_to_device = {}
        for device in indigo.devices.iter("self"):
            node_id = self._get_node_id(device)
            if node_id:
                self.node_to_device.setdefault(node_id, [])
                if device.id not in self.node_to_device[node_id]:
                    self.node_to_device[node_id].append(device.id)

    def _touch(self, device):
        """Update lastUpdate, mark device online, and clear any stale flag."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        device.updateStateOnServer("lastUpdate", value=ts)
        if device.id in self.stale_device_ids:
            self.stale_device_ids.discard(device.id)
            device.updateStateOnServer("deviceOnline", value=True, uiValue="online")
            self.logger.info(f"{device.name}: Back online (report received)")

    # -------------------------------------------------------------------------
    # Menu handlers
    # -------------------------------------------------------------------------

    def showPluginInfo(self, valuesDict=None, typeId=None):
        if log_startup_banner:
            log_startup_banner(self.pluginId, self.pluginDisplayName, self.pluginVersion)
        else:
            indigo.server.log(f"{self.pluginDisplayName} v{self.pluginVersion}")

#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    plugin.py
# Description: Universal Z-Wave Sensor - creates companion plugin devices
#              alongside existing Indigo Z-Wave devices, capturing sensor values
#              (temperature, humidity, contact, etc.) that Indigo does not expose
#              natively. Uses subscribeToIncoming() to receive ALL Z-Wave bytes.
# Author:      CliveS & Claude Sonnet 4.6
# Date:        22-03-2026
# Version:     3.2

import indigo
import struct
from datetime import datetime, timedelta


# ==============================================================================
# Z-Wave Command Class constants
# ==============================================================================

CC_BASIC                = 0x20
CC_SWITCH_BINARY        = 0x25
CC_SWITCH_MULTILEVEL    = 0x26
CC_SENSOR_BINARY        = 0x30
CC_SENSOR_MULTILEVEL    = 0x31
CC_METER                = 0x32
CC_MULTI_CHANNEL        = 0x60   # Multi-channel / endpoint encapsulation
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

# ==============================================================================
# SENSOR_MULTILEVEL (0x31) sensor type lookup
# key  -> (state_id, default_unit)
# ==============================================================================
SENSOR_TYPES = {
    0x01: ("temperature",  "degC"),
    0x03: ("luminance",    "lux"),
    0x05: ("humidity",     "%"),
    0x08: ("pressure",     "kPa"),
    0x0F: ("co2Level",     "ppm"),
    0x11: ("uvIndex",      ""),
    0x1B: ("noise",        "dB"),
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
}

# ==============================================================================
# NOTIFICATION (0x71) type and event constants
# ==============================================================================
NOTIF_SMOKE            = 0x01
NOTIF_CO               = 0x02
NOTIF_WATER            = 0x05
NOTIF_ACCESS_CONTROL   = 0x06
NOTIF_HOME_SECURITY    = 0x07
NOTIF_POWER            = 0x08

# HOME_SECURITY events
HS_MOTION_DETECTED     = 0x07
HS_MOTION_CLEARED      = 0x08
HS_TAMPER              = 0x03
HS_TAMPER_CLEARED      = 0x04
HS_IDLE                = 0x00   # generic idle — check what was cleared

# ACCESS_CONTROL events
AC_DOOR_OPEN           = 0x16
AC_DOOR_CLOSED         = 0x17

# ==============================================================================
# METER (0x32) electric scale lookup
# key -> (state_id, unit)
# ==============================================================================
METER_ELECTRIC         = 0x01
METER_GAS              = 0x02
METER_WATER            = 0x03

METER_ELECTRIC_SCALES = {
    0: ("kwh",   "kWh"),
    1: ("kwh",   "kVAh"),
    2: ("watts", "W"),
    # scale=3: pulse count (no useful state to write)
    # scale=4/5 (V/A) require METER_REPORT v3 extended scale — not yet implemented
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

    # ==========================================================================
    # Plugin lifecycle
    # ==========================================================================

    def startup(self):
        self.logger.info("Universal Z-Wave Sensor plugin starting v3.2")
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

    def deviceStartComm(self, device):
        self.logger.info(f"Starting: '{device.name}'")
        device.stateListOrDisplayStateIdChanged()
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
        self.logger.info(f"{device.name}: {state_key} = {ui_str}")
        device.updateStateOnServer(state_key, value=round(value, dp), uiValue=ui_str)

        # Update displayStatus when this report matches the device's primary sensor type
        dev_sensor_type = device.pluginProps.get("sensorType", "generic")
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

        self.logger.info(f"{device.name}: {state_key} = {label}")
        device.updateStateOnServer(state_key,       value=is_active, uiValue=label)
        device.updateStateOnServer("onOffState",    value=is_active)
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
            if notif_event == HS_MOTION_DETECTED:
                self.logger.info(f"{device.name}: Motion DETECTED")
                device.updateStateOnServer("motion",        value=True,  uiValue="detected")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="detected")
            elif notif_event == HS_MOTION_CLEARED:
                self.logger.info(f"{device.name}: Motion CLEARED")
                device.updateStateOnServer("motion",        value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            elif notif_event in (HS_TAMPER, 0x09):
                self.logger.info(f"{device.name}: Tamper DETECTED")
                device.updateStateOnServer("tamper",        value=True,  uiValue="tamper")
                device.updateStateOnServer("displayStatus", value="tamper")
            elif notif_event == HS_TAMPER_CLEARED:
                self.logger.info(f"{device.name}: Tamper CLEARED")
                device.updateStateOnServer("tamper",        value=False, uiValue="clear")
                device.updateStateOnServer("displayStatus", value="clear")
            elif notif_event == HS_IDLE:
                self.logger.info(f"{device.name}: Home security idle (all clear)")
                device.updateStateOnServer("motion",        value=False, uiValue="clear")
                device.updateStateOnServer("tamper",        value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            else:
                self.logger.info(
                    f"{device.name}: HOME_SECURITY event=0x{notif_event:02X} "
                    f"status=0x{notif_status:02X} (unhandled)"
                )
            self._touch(device)
            return True

        elif notif_type == NOTIF_ACCESS_CONTROL:
            if notif_event == AC_DOOR_OPEN:
                self.logger.info(f"{device.name}: Door/Window OPEN")
                device.updateStateOnServer("contact",       value=True,  uiValue="open")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="open")
            elif notif_event == AC_DOOR_CLOSED:
                self.logger.info(f"{device.name}: Door/Window CLOSED")
                device.updateStateOnServer("contact",       value=False, uiValue="closed")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="closed")
            else:
                self.logger.info(
                    f"{device.name}: ACCESS_CONTROL event=0x{notif_event:02X} (unhandled)"
                )
            self._touch(device)
            return True

        elif notif_type == NOTIF_WATER:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: Water LEAK detected")
                device.updateStateOnServer("waterLeak",     value=True,  uiValue="leak")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="leak")
            elif notif_event == 0x00 or notif_status == 0x00:
                self.logger.info(f"{device.name}: Water leak CLEARED")
                device.updateStateOnServer("waterLeak",     value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            self._touch(device)
            return True

        elif notif_type == NOTIF_SMOKE:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: Smoke DETECTED")
                device.updateStateOnServer("smoke",         value=True,  uiValue="smoke")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="smoke")
            elif notif_event == 0x00:
                self.logger.info(f"{device.name}: Smoke CLEARED")
                device.updateStateOnServer("smoke",         value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
            self._touch(device)
            return True

        elif notif_type == NOTIF_CO:
            if notif_event in (0x01, 0x02):
                self.logger.info(f"{device.name}: CO ALARM")
                device.updateStateOnServer("coAlarm",       value=True,  uiValue="alarm")
                device.updateStateOnServer("onOffState",    value=True)
                device.updateStateOnServer("displayStatus", value="alarm")
            elif notif_event == 0x00:
                self.logger.info(f"{device.name}: CO alarm CLEARED")
                device.updateStateOnServer("coAlarm",       value=False, uiValue="clear")
                device.updateStateOnServer("onOffState",    value=False)
                device.updateStateOnServer("displayStatus", value="clear")
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
        level: 0-100 = battery %   0xFF = battery low warning
        """
        if len(raw) < 3:
            return False

        level = raw[2]
        if level == 0xFF:
            self.logger.warning(f"{device.name}: Battery LOW")
            device.updateStateOnServer("batteryLevel", value=1, uiValue="LOW")
        else:
            self.logger.info(f"{device.name}: Battery = {level}%")
            device.updateStateOnServer("batteryLevel", value=level, uiValue=f"{level}%")
        self._touch(device)
        return True

    def _handle_meter(self, device, raw) -> bool:
        """
        METER_REPORT v2 (CC=0x32, cmd=0x02)
        Byte layout:
          [0x32, 0x02, meter_type_rate, prec_scale_size, value_bytes...]
          meter_type_rate: bits [6:5]=rate_type  [4:0]=meter_type
          prec_scale_size: bits [7:5]=precision  [4:3]=scale  [2:0]=size
        """
        if len(raw) < 6:
            return False

        meter_type_rate = raw[2]
        prec_scale_size = raw[3]
        meter_type      = meter_type_rate & 0x1F
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
            self.logger.error(f"{device.name}: METER parse error: {e}")
            return False

        value = raw_val / (10 ** precision)

        if meter_type == METER_ELECTRIC:
            scale_info = METER_ELECTRIC_SCALES.get(scale)
            if scale_info:
                state_key, unit = scale_info
                ui_str = f"{value:.3f} {unit}"
                self.logger.info(f"{device.name}: {state_key} = {ui_str}")
                device.updateStateOnServer(state_key,       value=round(value, 3), uiValue=ui_str)
                device.updateStateOnServer("displayStatus", value=ui_str)
                self._touch(device)
                return True

        self.logger.info(
            f"{device.name}: METER type=0x{meter_type:02X} scale={scale} "
            f"value={value} (add to METER_ELECTRIC_SCALES to handle)"
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
        device.updateStateOnServer("switchState",   value=is_on, uiValue=label)
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
        device.updateStateOnServer("dimLevel",      value=level, uiValue=f"{level}%")
        device.updateStateOnServer("switchState",   value=is_on)
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
        device.updateStateOnServer("dimLevel",   value=level, uiValue=str(level))
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
          Temperature 21.5 degC:   31 05 01 22 00 D7
          Motion detected (NOTIF): 71 05 00 00 00 FF 07 07 00
          Motion cleared  (NOTIF): 71 05 00 00 00 FF 07 08 00
          Door open       (NOTIF): 71 05 00 00 00 FF 06 16 00
          Door closed     (NOTIF): 71 05 00 00 00 FF 06 17 00
          Battery 85%:             80 03 55
          Wake-up interval 5min:   84 06 00 01 2C 6F
          Wake-up notification:    84 07
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
        Extract node_id and raw bytes from cmd dict.
        Key names vary between Indigo versions — tries common variants.
        If neither works, enable debug logging and inspect the logged dict.
        """
        node_id = cmd.get("nodeId",
                  cmd.get("sourceNodeId",
                  cmd.get("node_id", None)))

        raw = list(cmd.get("bytes",
               cmd.get("cmdBytes",
               cmd.get("rawBytes", []))))

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
        else:   # generic
            label = "on" if is_on else "off"
            device.updateStateOnServer("displayStatus", value=label)
            device.updateStateImageOnServer(
                indigo.kStateImageSel.SensorOn if is_on
                else indigo.kStateImageSel.SensorOff
            )

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

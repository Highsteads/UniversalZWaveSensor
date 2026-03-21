#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:    plugin.py
# Description: Universal Z-Wave Sensor - creates proper Indigo plugin devices
#              for Z-Wave sensors that Indigo does not natively recognise.
#              Parses raw Z-Wave command bytes via zwaveCommandReceived().
# Author:      CliveS & Claude Sonnet 4.6
# Date:        21-03-2026
# Version:     2.1

import indigo
import struct
from datetime import datetime


# ==============================================================================
# Z-Wave Command Class constants
# ==============================================================================

CC_BASIC                = 0x20
CC_SWITCH_BINARY        = 0x25
CC_SWITCH_MULTILEVEL    = 0x26
CC_SENSOR_BINARY        = 0x30
CC_SENSOR_MULTILEVEL    = 0x31
CC_METER                = 0x32
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
    # scale=4/5 (V/A) require METER_REPORT v3 extended scale (Scale2 byte) —
    # not yet implemented; the 2-bit mask (prec_scale_size >> 3) & 0x03
    # can only produce 0-3, so those entries would never be reached here.
}


# ==============================================================================
# Plugin class
# ==============================================================================

class Plugin(indigo.PluginBase):

    def __init__(self, plugin_id, display_name, version, prefs):
        super().__init__(plugin_id, display_name, version, prefs)
        self.debug        = prefs.get("showDebugInfo",    False)
        self.log_unknown  = prefs.get("logUnknownReports", True)
        # Maps Z-Wave node_id (int) -> list of Indigo device_ids (int)
        # One physical Z-Wave node can back multiple plugin devices (motion, temp, lux…)
        self.node_to_device: dict[int, list[int]] = {}

    # ==========================================================================
    # Plugin lifecycle
    # ==========================================================================

    def startup(self):
        self.logger.info("Universal Z-Wave Sensor plugin starting v2.1")
        self._rebuild_node_map()
        nodes = sorted(self.node_to_device.keys())
        self.logger.info(f"  Monitoring {len(nodes)} node(s): {nodes}")
        if self.debug:
            self.logger.debug("  Debug logging ENABLED")

    def shutdown(self):
        self.logger.info("Universal Z-Wave Sensor plugin stopping")

    def runConcurrentThread(self):
        try:
            while True:
                self.sleep(60)
        except self.StopThread:
            pass

    def closedPrefsConfigUi(self, values_dict, user_cancelled):
        if not user_cancelled:
            self.debug       = values_dict.get("showDebugInfo",    False)
            self.log_unknown = values_dict.get("logUnknownReports", True)
            self.logger.info(f"Prefs updated: debug={self.debug} log_unknown={self.log_unknown}")

    # ==========================================================================
    # Device lifecycle
    # ==========================================================================

    def deviceStartComm(self, device):
        self.logger.info(f"Starting: '{device.name}'")
        # Ensure device picks up any new states added since it was created
        device.stateListOrDisplayStateIdChanged()
        node_id = self._get_node_id(device)
        if node_id:
            if node_id not in self.node_to_device:
                self.node_to_device[node_id] = []
            if device.id not in self.node_to_device[node_id]:
                self.node_to_device[node_id].append(device.id)
            self.logger.info(f"  Now listening on Z-Wave Node {node_id}")
        else:
            self.logger.error(f"  No valid Node ID configured for '{device.name}' — edit device and set it")

    def deviceStopComm(self, device):
        node_id = self._get_node_id(device)
        if node_id and node_id in self.node_to_device:
            try:
                self.node_to_device[node_id].remove(device.id)
            except ValueError:
                pass
            # Only remove the node entry when no plugin devices remain on it
            if not self.node_to_device[node_id]:
                del self.node_to_device[node_id]
            self.logger.info(f"Stopped listening on Node {node_id}")

    def validateDeviceConfigUi(self, values_dict, type_id, device_id):
        errors   = indigo.Dict()
        node_str = values_dict.get("nodeId", "").strip()
        if not node_str.isdigit() or not (1 <= int(node_str) <= 232):
            errors["nodeId"] = "Node ID must be a whole number between 1 and 232"
        else:
            values_dict["address"] = node_str   # Indigo uses this as display address

            # Warn if Indigo already has a native device on this node.
            # zwaveCommandReceived() only fires for nodes this plugin owns —
            # if Indigo already owns the node, raw bytes will never arrive here
            # and this plugin device will never update.
            node_id = int(node_str)
            known_names = [
                dev.name for dev in indigo.devices
                if dev.pluginId != self.pluginId
                and dev.id != device_id
                and str(getattr(dev, "address", "")) == node_str
            ]
            if known_names:
                names_str = ", ".join(f"'{n}'" for n in known_names[:3])
                if len(known_names) > 3:
                    names_str += f" (+{len(known_names) - 3} more)"
                errors["nodeId"] = (
                    f"Node {node_id} already has Indigo-managed device(s): {names_str}. "
                    f"Indigo owns this node — zwaveCommandReceived() will not fire for it "
                    f"and this plugin device will never receive updates. "
                    f"Use the existing Indigo device(s) directly instead."
                )

        return (len(errors) == 0), values_dict, errors

    # ==========================================================================
    # Z-Wave report handler — plugin-owned unknown devices
    # NOTE: Only fires for devices whose Z-Wave node is owned by this plugin.
    #       Does NOT fire for nodes managed by Indigo's built-in Z-Wave handler.
    # ==========================================================================

    def zwaveCommandReceived(self, cmd):
        """
        Called by Indigo for every incoming Z-Wave command directed at the
        controller. Receives reports from ALL nodes — we filter to our own.

        A single node can back multiple plugin devices (motion, temp, lux…);
        we iterate over all of them and route the report to each.

        IMPORTANT: cmd key names can vary by Indigo version.
        Enable debug logging in plugin preferences to see the full cmd dict
        on first run. Adjust _extract_node_and_bytes() if keys differ.
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

        elif cmd_class == CC_WAKE_UP            and cmd_func == CMD_WAKE_UP_NOTIFICATION:
            self.logger.debug(f"{device.name}: Wake-up notification")
            handled = True

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

        # Resolve unit from scale byte
        if sensor_type == 0x01:   # temperature
            unit = "degC" if scale == 0 else "degF"
        elif sensor_type == 0x03:  # luminance
            unit = "%" if scale == 0 else "lux"
        else:
            unit = default_unit

        dp       = max(0, precision)
        ui_str   = f"{value:.{dp}f} {unit}".strip()
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
        device.updateStateOnServer(state_key,      value=is_active, uiValue=label)
        device.updateStateOnServer("onOffState",   value=is_active)
        device.updateStateOnServer("displayStatus", value=label)
        self._touch(device)
        return True

    def _handle_notification(self, device, raw) -> bool:
        """
        NOTIFICATION_REPORT v4+ (CC=0x71, cmd=0x05)
        Byte layout:
          [0x71, 0x05, 0x00, 0x00, 0x00, notif_type, notif_status, notif_event,
           event_params_len, event_params...]
          notif_status: 0xFF=active  0x00=idle
          notif_event:  0x00=idle/generic-cleared  >0=specific event
        """
        if len(raw) < 8:
            return False

        notif_type   = raw[5]
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

        raw_val      = raw[2]
        level        = 99 if raw_val == 0xFF else min(raw_val, 99)
        is_on        = level > 0
        display_str  = f"{level}%" if is_on else "off"
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

    # ==========================================================================
    # Helpers
    # ==========================================================================

    def _extract_node_and_bytes(self, cmd) -> tuple[int | None, list[int]]:
        """
        Extract node_id and raw bytes from cmd dict.
        Key names vary between Indigo versions — tries common variants.
        If neither works, enable debug logging and inspect the logged dict.
        """
        # Try known key names for node ID
        node_id = cmd.get("nodeId",
                  cmd.get("sourceNodeId",
                  cmd.get("node_id", None)))

        # Try known key names for byte list
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
        """Rebuild node_id -> [device_id, ...] map from all plugin devices.
        A single node can have multiple plugin devices (motion, temp, lux etc.)
        so the map stores a list of device IDs per node.
        """
        self.node_to_device = {}
        for device in indigo.devices.iter("self"):
            node_id = self._get_node_id(device)
            if node_id:
                self.node_to_device.setdefault(node_id, [])
                if device.id not in self.node_to_device[node_id]:
                    self.node_to_device[node_id].append(device.id)

    def _touch(self, device):
        """Update lastUpdate state with current timestamp."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        device.updateStateOnServer("lastUpdate", value=ts)

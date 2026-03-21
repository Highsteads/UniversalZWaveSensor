# Universal Z-Wave Sensor Plugin — User Manual

**Version 1.5** | Indigo 2025.1 | Author: CliveS & Claude Sonnet 4.6
**Last updated:** 21-Mar-2026

---

## Contents

1. [What this plugin does](#1-what-this-plugin-does)
2. [How it works — two paths](#2-how-it-works--two-paths)
3. [Installation](#3-installation)
4. [Creating your first device](#4-creating-your-first-device)
5. [Multi-sensor devices — one node, multiple plugin devices](#5-multi-sensor-devices--one-node-multiple-plugin-devices)
6. [Sensor types and device states](#6-sensor-types-and-device-states)
7. [Plugin preferences](#7-plugin-preferences)
8. [Working with unknown devices (raw Z-Wave path)](#8-working-with-unknown-devices--raw-z-wave-path)
9. [Z-Wave command classes handled](#9-z-wave-command-classes-handled)
10. [Triggers and automations](#10-triggers-and-automations)
11. [Troubleshooting](#11-troubleshooting)
12. [Known limitations](#12-known-limitations)
13. [Changelog](#13-changelog)

---

## 1. What this plugin does

Indigo has excellent native Z-Wave support, but there are always devices it does not fully recognise — newer sensors, less-common models, or multi-sensors where Indigo creates the devices but the states don't appear where you want them.

This plugin solves both problems. It lets you create a proper Indigo plugin device from any Z-Wave sensor — with the right icon, meaningful states, and a human-readable value in the device list — without waiting for official support.

**Typical use cases:**

- A multi-sensor (motion + temperature + luminance) where Indigo creates three native devices but you want a single, unified motion sensor device with all states in one place
- A door/window sensor that Indigo lists as "Unknown Z-Wave Device" with no states
- Any Z-Wave device you bought recently that Indigo does not yet have a definition for
- Mirroring Indigo's own Z-Wave devices into a cleaner custom device type with better displayStatus

---

## 2. How it works — two paths

### Path 1: Known devices (subscribeToChanges)

If Indigo already created a native device for your Z-Wave sensor, this path is used.

The plugin calls `indigo.devices.subscribeToChanges()` at startup and receives a callback every time any Indigo device changes state. When an update arrives for a device on a monitored node, the plugin reads the relevant states and mirrors them into the plugin device.

**Advantages:** No raw byte parsing. Indigo has already decoded the Z-Wave frames, applied the device definition, and stored typed values. The plugin just reads them.

**When to use:** Any Z-Wave device that appears in Indigo's device list with some states already working (even if they are in the wrong place, have the wrong type, or don't appear how you want them).

### Path 2: Unknown devices (zwaveCommandReceived)

If Indigo has no definition for your device, this path is used.

The plugin implements `zwaveCommandReceived()`, which receives the raw Z-Wave byte sequence for every incoming report. The plugin decodes the standard command classes directly from the bytes.

**Advantages:** Works for any Z-Wave device regardless of whether Indigo recognises it.

**When to use:** Devices that appear as "Unknown Z-Wave Device" in Indigo, or devices Indigo pairs but creates no states for.

**Note:** Leave the Source Indigo Device field blank when using this path.

### How the plugin chooses between paths

- If **Source Indigo Device** is set: uses Path 1 exclusively — only updates from that specific Indigo device are processed
- If **Source Indigo Device** is blank: uses Path 2 (raw Z-Wave bytes) for decoding; Path 1 may also fire if Indigo created any native device with the same node address

---

## 3. Installation

1. Download `UniversalZWaveSensor.indigoPlugin` from GitHub:
   https://github.com/Highsteads/UniversalZWaveSensor

2. Double-click the downloaded file — Indigo will prompt to install it

3. In Indigo, go to **Plugins menu → Universal Z-Wave Sensor → Enable**

4. The plugin starts immediately; no server restart required

---

## 4. Creating your first device

### Step 1 — Find the node ID

In Indigo, open **Devices** and look at the Z-Wave devices for your sensor. The node ID is shown in the address field or device details. It is a number between 1 and 232 (e.g. 223).

If the device is completely unrecognised, look in **Plugins → Z-Wave → Z-Wave Device Database** or check the Indigo log when the device sends a report.

### Step 2 — Create the plugin device

1. Go to **Devices → New Device**
2. Set Type to **Universal Z-Wave Sensor**
3. Set Model to **Universal Z-Wave Sensor**
4. Click **Edit Device Settings**

### Step 3 — Configure the device

| Field | Description |
|---|---|
| **Z-Wave Node ID** | The numeric node ID from Indigo's Z-Wave device list |
| **Sensor Type** | Sets the icon and what the displayStatus shows — choose the type that matches the sensor's primary function |
| **Source Indigo Device** | Select the specific Indigo native device to mirror from. Enter the Node ID first — the list will then show only devices on that node. Leave blank for unknown devices. |

### Step 4 — Save and test

Click **Save**. The plugin device appears in your device list. If a Source Indigo Device is set, it immediately reads the current value from that device (no need to wait for the next state change).

If using the raw Z-Wave path, enable debug logging in Plugin Preferences and trigger the physical sensor — you will see the raw bytes in the Indigo log.

---

## 5. Multi-sensor devices — one node, multiple plugin devices

Many Z-Wave multi-sensors report motion, temperature, and luminance all from the same node. Indigo itself handles this by creating three separate native devices, each with the same node address.

This plugin works the same way: create one plugin device per sensor type, all with the same node ID, each pointing to its own specific Source Indigo Device.

### Example — Neo NEOEMS02Z (Node 223)

Indigo creates:
- `Front Door Motion` (node 223, motion sensor)
- `Front Door Temperature` (node 223, temperature sensor)
- `Front Door Luminance` (node 223, luminance sensor)

Create three plugin devices:

| Plugin device name | Node ID | Sensor Type | Source Indigo Device |
|---|---|---|---|
| `223 Front Door Motion` | 223 | Motion Sensor | Front Door Motion |
| `223 Front Door Temperature` | 223 | Temperature Sensor | Front Door Temperature |
| `223 Front Door Luminance` | 223 | Luminance Sensor | Front Door Luminance |

**Why the Source Indigo Device field matters here:**
All three Indigo native devices share address "223". Without the Source filter, every plugin device would receive updates from all three sources, causing cross-contamination (e.g. the temperature plugin device receiving the lux value as temperature). Setting Source Indigo Device on each plugin device ensures it only processes updates from the correct source.

**Important:** Indigo's native Z-Wave sensor devices use `sensorValue` as their generic primary state. The plugin can only safely interpret `sensorValue` as temperature when the Source Indigo Device is set — because only then do we know the source is actually a temperature sensor. If Source is blank and the only state is `sensorValue`, the plugin logs a warning rather than guessing.

---

## 6. Sensor types and device states

### Motion Sensor
- **Icon:** Motion sensor (filled when detected)
- **displayStatus:** `detected` / `clear`
- **Key states:** `onOffState` (bool), `motion` (bool), `tamper` (bool)

### Contact Sensor (door/window)
- **Icon:** Sensor tripped / sensor off
- **displayStatus:** `open` / `closed`
- **Key states:** `onOffState` (bool), `contact` (bool)

### Temperature Sensor
- **Icon:** Thermometer
- **displayStatus:** `21.5 degC`
- **Key states:** `temperature` (float)

### Humidity Sensor
- **Icon:** Humidity sensor
- **displayStatus:** `65%`
- **Key states:** `humidity` (float)

### Luminance Sensor
- **Icon:** Light sensor
- **displayStatus:** `450 lux`
- **Key states:** `luminance` (float)

### Energy Monitor
- **Icon:** Power on/off
- **displayStatus:** `125.5 W`
- **Key states:** `watts` (float), `kwh` (float)

### Generic (on/off)
- **Icon:** Sensor on/off
- **displayStatus:** `on` / `off`
- **Key states:** `onOffState` (bool), `switchState` (bool), `dimLevel` (int)

### States available on ALL device types

| State | Type | Description |
|---|---|---|
| `displayStatus` | String | Human-readable primary value shown in device list |
| `onOffState` | Boolean | Generic on/off (set wherever applicable) |
| `batteryLevel` | Number | Battery % (1-100); `1` with uiValue `LOW` = 0xFF sentinel |
| `waterLeak` | Boolean | Water leak detected |
| `smoke` | Boolean | Smoke alarm active |
| `coAlarm` | Boolean | CO alarm active |
| `tamper` | Boolean | Tamper detection |
| `co2Level` | Number | CO2 in ppm |
| `uvIndex` | Number | UV index |
| `pressure` | Number | Barometric pressure in kPa |
| `noise` | Number | Noise level in dB |
| `voltage` | Number | Voltage in V (state reserved; requires METER v3 parser) |
| `current` | Number | Current in A (state reserved; requires METER v3 parser) |
| `lastUpdate` | String | Timestamp of last state change `YYYY-MM-DD HH:MM:SS` |
| `rawLastReport` | String | Hex bytes of last unrecognised report |

---

## 7. Plugin preferences

Access via **Plugins → Universal Z-Wave Sensor → Configure...**

| Setting | Default | Description |
|---|---|---|
| **Enable debug logging** | Off | Logs every incoming Z-Wave byte sequence, all state mirrors, and the full cmd dict. Use when setting up a new device. Turn off in normal use — it generates a lot of log entries. |
| **Log unknown command classes** | On | When the plugin receives a Z-Wave report it cannot decode, it logs the hex bytes and stores them in the `rawLastReport` state. Useful for identifying new command classes to add. |

---

## 8. Working with unknown devices (raw Z-Wave path)

If your device is not recognised by Indigo, follow this process:

### Step 1 — Pair the device

Pair it with Indigo's Z-Wave controller as normal. Note the node ID assigned (visible in the Z-Wave device list even if the device type is shown as unknown).

### Step 2 — Create a plugin device

Create a new Universal Z-Wave Sensor plugin device:
- Enter the node ID
- Choose the sensor type you expect (or Generic if unsure)
- Leave Source Indigo Device blank

### Step 3 — Enable debug logging

In Plugin Preferences, enable **Enable debug logging**.

### Step 4 — Trigger the device

Physically trigger the sensor (wave your hand in front of a motion sensor, open a door, etc.). In the Indigo log you will see:

```
Universal Z-Wave Sensor Debug   zwaveCommandReceived raw cmd: {'nodeId': 47, 'bytes': [49, 5, 1, 34, 0, 215], ...}
Universal Z-Wave Sensor Debug   Test Device [Node 47]: CC=0x31 func=0x05 [31 05 01 22 00 D7]
```

This tells you exactly which command class and bytes the device is sending. The plugin will attempt to decode them automatically.

### Step 5 — Check the states

If the command class is one the plugin handles (see section 9), the state will be written automatically and you will see it in the device inspector.

If you see `Unhandled CC=0xXX` in the log, that command class is not yet implemented. The hex bytes are stored in `rawLastReport` for investigation.

### Step 6 — Disable debug logging

Once the device is working correctly, turn off debug logging.

---

## 9. Z-Wave command classes handled

### SENSOR_MULTILEVEL (0x31) — report 0x05

Decodes continuous sensor values. The sensor type byte in the report determines the state written.

| Sensor type byte | State written | Units |
|---|---|---|
| 0x01 | `temperature` | degC or degF (from scale byte) |
| 0x03 | `luminance` | % or lux (from scale byte) |
| 0x05 | `humidity` | % |
| 0x08 | `pressure` | kPa |
| 0x0F | `co2Level` | ppm |
| 0x11 | `uvIndex` | (dimensionless) |
| 0x1B | `noise` | dB |

Precision and size are decoded from the `prec_scale_size` byte. Handles 1, 2, and 4-byte signed big-endian values.

### SENSOR_BINARY (0x30) — report 0x03

| Sensor type byte | State written | Values |
|---|---|---|
| 0x01 (general) | `onOffState` | True/False |
| 0x02 | `smoke` | True=smoke, False=clear |
| 0x03 | `coAlarm` | True=alarm, False=clear |
| 0x04 | `waterLeak` | True=leak, False=clear |
| 0x06 | `tamper` | True=tamper, False=clear |
| 0x08 / 0x09 / 0x0B | `motion` | True=detected, False=clear |
| 0x0A | `contact` | True=open, False=closed |

v1 frames (no sensor type byte) fall back to `onOffState`.

### NOTIFICATION v4+ (0x71) — report 0x05

| Notification type | Event | State written |
|---|---|---|
| HOME_SECURITY (0x07) | 0x07 Motion detected | `motion=True`, `onOffState=True` |
| HOME_SECURITY (0x07) | 0x08 Motion cleared | `motion=False`, `onOffState=False` |
| HOME_SECURITY (0x07) | 0x03/0x09 Tamper | `tamper=True` |
| HOME_SECURITY (0x07) | 0x04 Tamper cleared | `tamper=False` |
| HOME_SECURITY (0x07) | 0x00 Idle | clears `motion` and `tamper` |
| ACCESS_CONTROL (0x06) | 0x16 Door open | `contact=True`, `onOffState=True` |
| ACCESS_CONTROL (0x06) | 0x17 Door closed | `contact=False`, `onOffState=False` |
| WATER (0x05) | 0x01/0x02 Leak | `waterLeak=True`, `onOffState=True` |
| WATER (0x05) | 0x00 Cleared | `waterLeak=False`, `onOffState=False` |
| SMOKE (0x01) | 0x01/0x02 Smoke | `smoke=True`, `onOffState=True` |
| SMOKE (0x01) | 0x00 Cleared | `smoke=False`, `onOffState=False` |
| CO (0x02) | 0x01/0x02 Alarm | `coAlarm=True`, `onOffState=True` |
| CO (0x02) | 0x00 Cleared | `coAlarm=False`, `onOffState=False` |

### METER (0x32) — report 0x02

Electric meter (type 0x01) scales:

| Scale | State written | Unit |
|---|---|---|
| 0 | `kwh` | kWh |
| 1 | `kwh` | kVAh |
| 2 | `watts` | W |

Note: Voltage (V) and current (A) require METER_REPORT v3 extended scale encoding — not yet implemented.

### SWITCH_BINARY (0x25) — report 0x03

`0xFF` = on, `0x00` = off. Writes `switchState`, `onOffState`, `displayStatus`.

### SWITCH_MULTILEVEL (0x26) — report 0x03

0–99 = dim level %, `0xFF` = restore last level (treated as 99%). Writes `dimLevel`, `onOffState`, `displayStatus`.

### BATTERY (0x80) — report 0x03

0–100 = battery %. `0xFF` = low battery sentinel (written as value=1, uiValue=`LOW`, warning logged).

### BASIC (0x20) — report 0x03

Legacy on/off. `0xFF` = on (99), `0x00` = off. Writes `dimLevel` and `onOffState`.

### WAKE_UP (0x84) — notification 0x07

Logged as a debug message. No state written — the device has simply woken up to send its reports.

---

## 10. Triggers and automations

Every state on the plugin device can be used as a trigger in Indigo.

**Useful trigger states:**

| Use case | Trigger on |
|---|---|
| Motion alert | `motion` changes to True |
| Door opened | `contact` changes to True |
| Door closed | `contact` changes to False |
| Temperature threshold | `temperature` becomes greater than N |
| Low battery | `batteryLevel` becomes less than 20 |
| Water leak | `waterLeak` changes to True |
| Smoke alarm | `smoke` changes to True |
| Display value changes | `displayStatus` changes |

The `onOffState` is set on all device types wherever meaningful, so standard Indigo triggers like "device turns on" also work.

---

## 11. Troubleshooting

### Plugin device shows stale value after Indigo restart

**Cause:** If you are using Path 1 (Source Indigo Device set), the initial sync should happen automatically on `deviceStartComm`. If Source is blank and the device is battery-powered, it will only update when the device next sends a report.

**Fix:** Check that Source Indigo Device is set. For battery devices on the raw path, physically trigger the device to force a report.

### Temperature sensor is showing lux value (or similar cross-contamination)

**Cause:** Source Indigo Device is not set, and multiple Indigo native devices on the same node all share the same `sensorValue` state name.

**Fix:** Set Source Indigo Device on each plugin device to point to its specific native source. See section 5.

### Plugin log shows "source device has only sensorValue but no sourceDeviceId"

**Cause:** The temperature plugin device has no Source Indigo Device set, and the source device's only state is `sensorValue` (which is ambiguous — it could be temperature or luminance).

**Fix:** Edit the plugin device and select the correct Source Indigo Device from the dropdown.

### No states appear after creating the device

**Cause (Path 1):** Source Indigo Device is set but that device has not changed state since the plugin restarted. Wait for a state change, or check the initial sync logged message.

**Cause (Path 2):** Device may not be sending reports, or the command class is not one the plugin handles.

**Fix:** Enable debug logging and trigger the device. If you see `CC=0xXX` in the log, the report is arriving. If you see `Unhandled CC=0xXX`, that class needs to be added.

### "No valid Node ID configured" error in log

**Cause:** The Node ID field was left blank or contains a non-numeric value.

**Fix:** Edit the device, enter the numeric node ID (1–232), and save.

### Multiple plugin devices on the same node are updating from wrong sources

**Cause:** Source Indigo Device is not set on one or more plugin devices.

**Fix:** Set Source Indigo Device on every plugin device. Each should point to a different native Indigo device.

### Log is flooded with debug output

**Fix:** Disable **Enable debug logging** in Plugin Preferences.

---

## 12. Known limitations

| Limitation | Detail |
|---|---|
| Battery devices | Only report on state change or scheduled wake-up. Cannot be polled on demand. The initial state sync at startup will reflect the last known value from when Indigo stored it, which may be hours old. |
| Multi-channel Z-Wave devices | Endpoint routing (channel addressing) is not yet implemented. Reports from individual endpoints may not be correctly attributed. |
| METER_REPORT v3+ | Voltage (V) and current (A) require the extended Scale2 byte introduced in v3. The current parser handles v2 only (kWh, kVAh, W). |
| S2 security | Indigo decrypts S2-encrypted frames before delivering them to plugins. The plugin only sees the decrypted payload — transparent to both paths. |
| Proprietary command classes | 0xF0 and above are manufacturer-specific. The plugin logs the raw bytes in `rawLastReport` but does not decode them. |
| Indigo device not yet created | If Indigo has not created any device at all for a node (extremely rare), Path 2 may still receive raw bytes, but the Source Indigo Device list will be empty. |

---

## 13. Changelog

| Version | Date | Summary |
|---|---|---|
| **1.5** | 21-Mar-2026 | Fixed `_handle_multilevel` hardcoding SensorOn for all types; removed unreachable V/A scale entries from METER_ELECTRIC_SCALES |
| **1.4** | 21-Mar-2026 | Correct icons across all code paths: TemperatureSensor, HumiditySensor, LightSensor for respective types |
| **1.3** | 21-Mar-2026 | Initial state sync on deviceStartComm — plugin device immediately reflects current source state on restart |
| **1.2** | 21-Mar-2026 | sensorValue blocked as temperature fallback when no sourceDeviceId set; warning logged with actionable message |
| **1.1** | 20-Mar-2026 | Critical fix: own plugin devices skipped in deviceUpdated to prevent infinite feedback loop |
| **1.0** | 20-Mar-2026 | Initial release — two-path architecture, 8 command classes, 7 sensor types |

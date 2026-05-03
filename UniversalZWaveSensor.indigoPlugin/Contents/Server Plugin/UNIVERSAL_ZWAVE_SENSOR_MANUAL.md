# Universal Z-Wave Sensor Plugin — User Manual

**Version 5.0** | Indigo 2025.1+ | Author: CliveS & Claude Sonnet 4.6
**Last updated:** 03-May-2026

---

## Contents

1. [What this plugin does](#1-what-this-plugin-does)
2. [How it works](#2-how-it-works)
3. [Installation](#3-installation)
4. [Upgrading from a previous version](#4-upgrading-from-a-previous-version)
5. [Creating a device](#5-creating-a-device)
6. [Multi-sensor devices — one node, multiple plugin devices](#6-multi-sensor-devices--one-node-multiple-plugin-devices)
7. [Multi-channel devices — endpoint routing](#7-multi-channel-devices--endpoint-routing)
8. [Sensor types and device states](#8-sensor-types-and-device-states)
9. [Plugin preferences](#9-plugin-preferences)
10. [Simulate Z-Wave Report](#10-simulate-z-wave-report)
11. [Stale device detection](#11-stale-device-detection)
12. [Z-Wave command classes handled](#12-z-wave-command-classes-handled)
13. [Triggers and automations](#13-triggers-and-automations)
14. [Troubleshooting](#14-troubleshooting)
15. [Known limitations](#15-known-limitations)
16. [Changelog](#16-changelog)

---

## 1. What this plugin does

When Indigo includes a Z-Wave sensor it creates a native device based on what it recognises. That works well for the values Indigo knows about. But many sensors send additional data that Indigo ignores — a door/window sensor that also reports temperature, a multi-sensor where Indigo captures motion but not humidity or luminance, a lock that sends detailed bolt and latch state, a scene controller Indigo doesn't support at all.

This plugin fills that gap. You select the existing native Indigo device, choose the sensor type you want to capture (temperature, humidity, contact, lock, scene, etc.), and the plugin creates a properly-typed Indigo device with the right icon, meaningful states, and a human-readable value in the device list.

**Typical use cases:**

- A NEO Coolcam door/window sensor that Indigo handles as a contact device, but which also sends temperature and humidity
- A motion sensor that also reports luminance and CO2 that Indigo does not expose
- A Z-Wave lock where you want bolt state, latch state, and the last user ID in Indigo variables
- A scene controller / remote that Indigo does not natively decode
- Any multi-sensor where Indigo captures one value but you want the others

**Reporting to Indigo developers:** The Simulate Z-Wave Report tool lets you feed raw byte sequences and see how the plugin parses them. If you want to help Matt and Jay (Indigo's authors) add native support for a sensor, enable debug logging, trigger the sensor, and send them the logged byte sequences.

---

## 2. How it works

At startup the plugin calls `indigo.zwave.subscribeToIncoming()`. This tells Indigo to deliver every incoming Z-Wave byte sequence to the plugin's `zwaveCommandReceived()` callback — for all nodes, not just nodes the plugin owns.

The plugin decodes the standard Z-Wave command classes directly from the bytes, writes the appropriate states on the matching plugin device, and keeps `lastUpdate`, `displayStatus`, and `onOffState` current at all times.

**Node matching:** When a report arrives, the plugin looks up which plugin device(s) are configured for that node ID (and optionally that endpoint). Only matching devices are updated. The native Indigo device on the same node is unaffected — both receive the same bytes simultaneously.

---

## 3. Installation

1. Go to the [Releases page](https://github.com/Highsteads/UniversalZWaveSensor/releases) and download `UniversalZWaveSensor.indigoPlugin.zip`

2. Unzip the downloaded file — you will get `UniversalZWaveSensor.indigoPlugin`

3. Double-click `UniversalZWaveSensor.indigoPlugin` — Indigo will install it automatically

4. In Indigo, go to **Plugins menu → Universal Z-Wave Sensor → Enable**

5. The plugin starts immediately; no server restart required

---

## 4. Upgrading from a previous version

Existing plugin devices upgrade automatically. When Indigo loads the new plugin version, it calls `device.stateListOrDisplayStateIdChanged()` on each device, which adds any new states with default values.

No manual steps are needed. Your existing triggers, control pages, and action groups continue to work unchanged.

If you previously had devices configured as Energy Monitor and want to also expose voltage and current, those states are now populated automatically by the existing parser — no reconfiguration needed.

---

## 5. Creating a device

### Step 1 — Include the sensor in Indigo

Include the sensor in your Z-Wave network through Indigo as normal. Indigo creates a native device for it. This native device is what the plugin reads the node ID from.

### Step 2 — Create the plugin device

1. Go to **Devices → New Device**
2. Set Type to **Universal Z-Wave Sensor**
3. Set Model to **Universal Z-Wave Sensor**
4. Click **Edit Device Settings**

### Step 3 — Configure the device

| Field | Description |
|---|---|
| **Native Indigo Z-Wave Device** | Select the existing Indigo device for this sensor — node ID is read automatically |
| **Sensor Type** | Sets the icon and what the displayStatus shows — choose the type for the value you want to capture |
| **Endpoint ID** | Optional. For multi-channel devices, enter the endpoint number (e.g. `1`, `2`, `3`). Leave blank or `0` to accept reports from all endpoints on this node. |

### Step 4 — Name and save

Name the device to reflect what it captures, e.g. `Bathroom Door (Temp)` or `Front Door Lock`. Click **Save**.

Enable debug logging in Plugin Preferences and trigger the physical sensor — you will see the raw bytes in the Indigo log and the states updating in real time.

### When Indigo adds native support

If Indigo adds full native support for the extra sensor values, delete the plugin devices and update any triggers or action groups that reference them. This is a one-time task.

---

## 6. Multi-sensor devices — one node, multiple plugin devices

Many Z-Wave sensors report motion, temperature, humidity, and more from the same node. Create one plugin device per sensor type, all selecting the same native device, each with the appropriate sensor type.

### Example — NEO Coolcam NAS-DS07ZE (door/window + temperature + humidity)

Indigo creates a native contact device for this sensor. The sensor also sends temperature and humidity that Indigo ignores.

Create two plugin devices, both selecting the same native Indigo device:

| Plugin device name | Sensor Type | Endpoint ID |
|---|---|---|
| `Bathroom Door (Temp)` | Temperature Sensor | (blank) |
| `Bathroom Door (Humidity)` | Humidity Sensor | (blank) |

Both devices receive every report from the node. Each only writes states relevant to its type — the temperature device writes `temperature` from SENSOR_MULTILEVEL reports; the humidity device writes `humidity`. The native Indigo contact device continues to handle door open/closed as before.

---

## 7. Multi-channel devices — endpoint routing

Some Z-Wave multi-sensors (e.g. Aeotec MultiSensor 6) use multi-channel addressing: each sensor type is exposed as a separate endpoint on the same node, using CC 0x60 MULTI_CHANNEL encapsulation.

The plugin unwraps CC 0x60 frames automatically and routes the inner payload to the appropriate plugin device based on the source endpoint in the frame.

### Setup for a 3-in-1 sensor (motion ep 1, temperature ep 2, luminance ep 3) on node 42

| Plugin device name | Sensor Type | Endpoint ID |
|---|---|---|
| Hall Motion | Motion Sensor | 1 |
| Hall Temperature | Temperature Sensor | 2 |
| Hall Luminance | Luminance Sensor | 3 |

Each plugin device only processes reports whose source endpoint matches its configured Endpoint ID. If Endpoint ID is blank or `0`, the device accepts reports from all endpoints on the node.

### Checking the endpoint number

Enable debug logging and trigger the device. The log will show:

```
Universal Z-Wave Sensor Debug   [Node 42] CC=0x60 Multi-Channel ep1->0 wrapping CC=0x31
Universal Z-Wave Sensor Debug   Hall Temperature [Node 42 ep 2]: CC=0x31 func=0x05 [31 05 01 22 00 D7]
```

The `ep1` in the first line is the source endpoint number to use in the Endpoint ID field.

---

## 8. Sensor types and device states

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
- **displayStatus:** `21.5 degC` (or degF per preference)
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
- **Key states:** `watts` (float), `kwh` (float), `voltage` (float), `current` (float)

### Battery Sensor
- **Icon:** Generic sensor
- **displayStatus:** `85%` or `LOW`
- **Key states:** `batteryLevel` (int, 0-100), `batteryLow` (bool), `onOffState` (bool — True when low)
- **Note:** All sensor types carry `batteryLevel` and `batteryLow` regardless of their type. The dedicated Battery Sensor type is for nodes that report nothing but battery state (e.g. a simple Z-Wave battery monitoring device).

### Lock (door lock)
- **Icon:** Lock
- **displayStatus:** `locked` / `unlocked`
- **Key states:** `lockState` (bool — True=locked), `lockMode` (int — raw mode byte), `boltState` (bool — True=bolt locked), `latchState` (bool — True=latch closed), `lastUser` (int — user ID from keypad/RF events), `onOffState` (bool)
- **Sources:** DOOR_LOCK_OPERATION_REPORT (CC 0x62) and NOTIFICATION ACCESS_CONTROL events (CC 0x71)

### Scene Controller (button/remote)
- **Icon:** Generic sensor
- **displayStatus:** `S1 pressed`, `S2 held`, etc.
- **Key states:** `lastScene` (int — scene number), `lastSceneAction` (string — pressed/released/held/repeated_1/repeated_2), `sceneTimestamp` (string — `YYYY-MM-DD HH:MM:SS`), `onOffState` (bool — True while key held/pressed, False on release)

### Generic (on/off)
- **Icon:** Sensor on/off
- **displayStatus:** `on` / `off`
- **Key states:** `onOffState` (bool), `switchState` (bool), `dimLevel` (int)

### States available on ALL device types

| State | Type | Description |
|---|---|---|
| `displayStatus` | String | Human-readable primary value shown in device list |
| `onOffState` | Boolean | Generic on/off (set wherever applicable) |
| `batteryLevel` | Number | Battery % (1-100); uiValue `LOW` when sentinel 0xFF received |
| `batteryLow` | Boolean | True if battery ≤ 20% or 0xFF sentinel received |
| `deviceOnline` | Boolean | True = recently reported; False = silent beyond stale threshold |
| `wakeUpInterval` | Number | Wake-up interval in seconds (from WAKE_UP_INTERVAL_REPORT) |
| `waterLeak` | Boolean | Water leak detected |
| `smoke` | Boolean | Smoke alarm active |
| `coAlarm` | Boolean | CO alarm active |
| `tamper` | Boolean | Tamper detection |
| `co2Level` | Number | CO2 in ppm |
| `uvIndex` | Number | UV index |
| `pressure` | Number | Barometric pressure in kPa |
| `noise` | Number | Noise level in dB |
| `velocity` | Number | Velocity in m/s |
| `airFlow` | Number | Air flow in m3/h |
| `voc` | Number | VOC level in ppm |
| `soilMoisture` | Number | Soil moisture % |
| `gasCubicMeters` | Number | Gas consumption in m3 (or ft3/ccf depending on meter scale) |
| `waterCubicMeters` | Number | Water consumption in m3 (or ft3/gallons depending on meter scale) |
| `voltage` | Number | Voltage in V |
| `current` | Number | Current in A |
| `lastUpdate` | String | Timestamp of last state change `YYYY-MM-DD HH:MM:SS` |
| `rawLastReport` | String | Hex bytes of last unrecognised report |

---

## 9. Plugin preferences

Access via **Plugins → Universal Z-Wave Sensor → Configure...**

| Setting | Default | Description |
|---|---|---|
| **Enable debug logging** | Off | Logs every incoming Z-Wave byte sequence and all state updates. Use when setting up a new device. Turn off in normal use. |
| **Log unknown command classes** | On | When the plugin receives a report it cannot decode, it logs the hex bytes and stores them in `rawLastReport`. |
| **Temperature unit** | degC | Choose **degC** or **degF** — all temperature values are stored and displayed in this unit. Reports in the opposite unit are converted automatically at ingest. |
| **Enable stale device detection** | On | Warns when a device has not sent any report within the configured threshold and marks it offline. |
| **Stale threshold** | 24 hours | How long without any report before a device is flagged as offline. Options: 4 / 8 / 12 / 24 / 48 / 72 hours. |

---

## 10. Simulate Z-Wave Report

**Plugins → Universal Z-Wave Sensor → Simulate Z-Wave Report...**

Select a plugin device, enter space-separated hex bytes, and click **Send**. The bytes are fed directly into the parser as if the real hardware had sent them. The dialog stays open so you can send multiple sequences in one session without reopening it.

This tool is also useful for capturing raw bytes from sensors and sharing them with the Indigo developers (Matt and Jay) to help them add or improve native support.

### Common byte sequences

| Byte sequence | What it simulates |
|---|---|
| `31 05 01 22 00 D7` | Temperature 21.5 degC |
| `31 05 03 0A 01 C2` | Luminance 450 lux |
| `31 05 05 01 41` | Humidity 65% |
| `71 05 00 00 00 FF 07 07 00` | Motion detected (NOTIFICATION, location provided) |
| `71 05 00 00 00 FF 07 00 00` | Motion cleared (HOME_SECURITY idle) |
| `71 05 00 00 00 FF 06 16 00` | Door opened (ACCESS_CONTROL) |
| `71 05 00 00 00 FF 06 17 00` | Door closed (ACCESS_CONTROL) |
| `71 05 00 00 00 FF 06 01 01 00` | Manual lock (no user ID) |
| `71 05 00 00 00 FF 06 05 01 00` | Keypad lock (no user ID) |
| `71 05 00 00 00 FF 06 06 02 05` | Keypad unlock (user 5) |
| `62 03 FF 00 00 FE` | Lock report — locked (v2, bolt locked, latch closed) |
| `62 03 00 00 00 FD` | Lock report — unlocked (v2, bolt unlocked, latch open) |
| `5B 03 01 00 01` | Central Scene — scene 1, key pressed |
| `5B 03 02 01 01` | Central Scene — scene 1, key released |
| `5B 03 03 02 02` | Central Scene — scene 2, key held |
| `5B 03 04 03 03` | Central Scene — scene 3, key repeated (1st) |
| `80 03 55` | Battery 85% |
| `80 03 FF` | Battery LOW warning |
| `84 07` | Wake-up notification (marks device alive) |
| `84 06 00 01 2C 6F` | Wake-up interval report = 300 s |
| `60 0D 00 01 31 05 01 22 00 D7` | Multi-channel ep 1: temperature 21.5 degC |

### Byte format reference

**SENSOR_MULTILEVEL (0x31) report:** `31 05 <type> <prec_scale_size> <value bytes...>`
- Type `01` = temperature, `03` = luminance, `05` = humidity, `08` = pressure, `0B` = velocity, `0F` = CO2, `10` = watts, `11` = UV index, `12` = voltage, `13` = current, `15` = air flow, `19` = VOC, `1B` = noise, `1C` = soil moisture
- `prec_scale_size` encodes precision (bits 7-5), scale (bits 4-3), size (bits 2-0)

**NOTIFICATION (0x71) report:** `71 05 00 00 00 FF <notif_type> <event> <params_len> [params...]`
- Notif status `FF` = event active, `00` = event cleared
- Notif type `07` = HOME_SECURITY, `06` = ACCESS_CONTROL, `05` = WATER, `01` = SMOKE, `02` = CO
- HOME_SECURITY events: `01/02` = intrusion, `03/09` = tamper, `05/06` = glass break, `07/08` = motion detected
- ACCESS_CONTROL events: `01` = manual lock, `02` = manual unlock, `03` = RF lock, `04` = RF unlock, `05` = keypad lock, `06` = keypad unlock, `09` = auto lock, `0B` = lock jammed

**DOOR_LOCK_OPERATION_REPORT (0x62 0x03):** `62 03 <mode> <handles_mode> <cond> <timeout>`
- Mode: `0xFF` = locked, `0x00` = unlocked
- Door condition byte (v2): bit0 = door open, bit1 = bolt not locked (inverted), bit2 = latch not closed (inverted)

**CENTRAL_SCENE_NOTIFICATION (0x5B 0x03):** `5B 03 <seq_no> <key_attributes> <scene_number>`
- Key attributes bits[2:0]: `0x00` = pressed, `0x01` = released, `0x02` = held, `0x03` = repeated_1, `0x04` = repeated_2, etc.

**BATTERY (0x80) report:** `80 03 <level>`
- Level = 0x00 to 0x64 (0-100%), 0xFF = low battery

**WAKE_UP_INTERVAL_REPORT (0x84 0x06):** `84 06 <b1> <b2> <b3> <node_id>`
- Interval seconds = (b1 << 16) | (b2 << 8) | b3

---

## 11. Stale device detection

The plugin checks all plugin devices every 60 seconds. If a device's `lastUpdate` timestamp is older than the configured stale threshold:

- A warning is logged once: `Sensor: No report for 26.3h (threshold 24h) — may be offline or out of range`
- `deviceOnline` state is set to `False` (uiValue `offline`)
- The warning is only logged **once per stale period** — no log flooding

When any Z-Wave report arrives from the device:

- `deviceOnline` is immediately set back to `True`
- `Back online (report received)` is logged
- The stale flag is cleared, so the next silence period starts fresh

### Choosing a threshold

| Device type | Suggested threshold |
|---|---|
| Mains-powered sensor | 4–8 hours |
| Battery sensor reporting hourly | 8–12 hours |
| Battery sensor with daily check-in | 48 hours |
| Very-low-power sensor (weekly wake-up) | 72 hours |

---

## 12. Z-Wave command classes handled

### SENSOR_MULTILEVEL (0x31) — report 0x05

| Sensor type byte | State written | Units |
|---|---|---|
| 0x01 | `temperature` | degC or degF (converted per preference) |
| 0x03 | `luminance` | % or lux (from scale byte) |
| 0x05 | `humidity` | % |
| 0x08 | `pressure` | kPa |
| 0x0B | `velocity` | m/s |
| 0x0F | `co2Level` | ppm |
| 0x10 | `watts` | W |
| 0x11 | `uvIndex` | (dimensionless) |
| 0x12 | `voltage` | V |
| 0x13 | `current` | A |
| 0x15 | `airFlow` | m3/h |
| 0x19 | `voc` | ppm |
| 0x1B | `noise` | dB |
| 0x1C | `soilMoisture` | % |

Precision and size are decoded from the `prec_scale_size` byte. Handles 1, 2, and 4-byte signed big-endian values.

### SENSOR_BINARY (0x30) — report 0x03

| Sensor type byte | State written | Values |
|---|---|---|
| 0x01 (general) | `onOffState` | True/False |
| 0x02 | `smoke` | True=smoke, False=clear |
| 0x03 | `coAlarm` | True=alarm, False=clear |
| 0x04 | `waterLeak` | True=leak, False=clear |
| 0x06 | `tamper` | True=tamper, False=clear |
| 0x08 / 0x09 / 0x0B / 0x0C | `motion` | True=detected, False=clear |
| 0x0A | `contact` | True=open, False=closed |

v1 frames (no sensor type byte) fall back to `onOffState`.

### NOTIFICATION v4+ (0x71) — report 0x05

The plugin auto-detects byte order: if raw[5] is `0x00` or `0xFF` the frame is Z-Wave spec order (status at byte 5, type at byte 6); otherwise reversed order is assumed.

| Notification type | Event | State written |
|---|---|---|
| HOME_SECURITY (0x07) | 0x01/0x02 Intrusion | `motion=True`, `onOffState=True` |
| HOME_SECURITY (0x07) | 0x05/0x06 Glass break | `motion=True`, `onOffState=True` |
| HOME_SECURITY (0x07) | 0x07 Motion detected (location provided) | `motion=True`, `onOffState=True` |
| HOME_SECURITY (0x07) | 0x08 Motion detected (unknown location) | `motion=True`, `onOffState=True` |
| HOME_SECURITY (0x07) | 0x03/0x09 Tamper | `tamper=True` |
| HOME_SECURITY (0x07) | 0x00 Idle (all clear) | clears `motion` and `tamper` |
| ACCESS_CONTROL (0x06) | 0x01 Manual lock | `lockState=True`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x02 Manual unlock | `lockState=False`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x03 RF lock | `lockState=True`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x04 RF unlock | `lockState=False`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x05 Keypad lock | `lockState=True`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x06 Keypad unlock | `lockState=False`, `lastUser` updated |
| ACCESS_CONTROL (0x06) | 0x09 Auto lock | `lockState=True` |
| ACCESS_CONTROL (0x06) | 0x0B Lock jammed | logged as warning |
| ACCESS_CONTROL (0x06) | 0x16 Door open | `contact=True`, `onOffState=True` |
| ACCESS_CONTROL (0x06) | 0x17 Door closed | `contact=False`, `onOffState=False` |
| WATER (0x05) | 0x01/0x02 Leak | `waterLeak=True`, `onOffState=True` |
| WATER (0x05) | 0x00 Cleared | `waterLeak=False`, `onOffState=False` |
| SMOKE (0x01) | 0x01/0x02 Smoke | `smoke=True`, `onOffState=True` |
| SMOKE (0x01) | 0x00 Cleared | `smoke=False`, `onOffState=False` |
| CO (0x02) | 0x01/0x02 Alarm | `coAlarm=True`, `onOffState=True` |
| CO (0x02) | 0x00 Cleared | `coAlarm=False`, `onOffState=False` |

### DOOR_LOCK (0x62) — OPERATION_REPORT 0x03

Decodes the full lock report directly from the lock hardware:

| Field | State | Notes |
|---|---|---|
| Mode byte `0xFF` | `lockState=True` | Locked |
| Mode byte `0x00` | `lockState=False` | Unlocked |
| Door condition bit1 (inverted) | `boltState` | True = bolt locked |
| Door condition bit2 (inverted) | `latchState` | True = latch closed |
| Raw mode byte | `lockMode` | Full mode value |

v2+ frames (5 bytes minimum): door condition byte extracted. v1 frames: bolt/latch states not available.

### CENTRAL_SCENE (0x5B) — NOTIFICATION 0x03

Decodes button/remote scene events:

| Field | State | Notes |
|---|---|---|
| Scene number (byte 4) | `lastScene` | 1-based scene number |
| Key attributes bits[2:0] | `lastSceneAction` | `pressed`, `released`, `held`, `repeated_1`, `repeated_2`... |
| Timestamp | `sceneTimestamp` | `YYYY-MM-DD HH:MM:SS` |
| Any non-release action | `onOffState=True` | |
| Release action | `onOffState=False` | |

### METER (0x32) — report 0x02

| Meter type | Scale | State written | Unit |
|---|---|---|---|
| Electric (0) | 0 | `kwh` | kWh |
| Electric (0) | 1 | `kwh` | kVAh |
| Electric (0) | 2 | `watts` | W |
| Electric (0) | 4 (Scale2) | `voltage` | V |
| Electric (0) | 5 (Scale2) | `current` | A |
| Gas (1) | 0 | `gasCubicMeters` | m3 |
| Gas (1) | 1 | `gasCubicMeters` | ft3 |
| Gas (1) | 2 | `gasCubicMeters` | ccf |
| Water (2) | 0 | `waterCubicMeters` | m3 |
| Water (2) | 1 | `waterCubicMeters` | ft3 |
| Water (2) | 2 | `waterCubicMeters` | gallons |

Voltage and current use METER_REPORT v3 Scale2 bit encoding: the Scale2 bit (byte 2 bit 7) is extracted and combined with the 2-bit scale field to form the full 3-bit scale value.

### SWITCH_BINARY (0x25) — report 0x03

`0xFF` = on, `0x00` = off. Writes `switchState`, `onOffState`, `displayStatus`.

### SWITCH_MULTILEVEL (0x26) — report 0x03

0–99 = dim level %, `0xFF` = restore last level (treated as 99%). Writes `dimLevel`, `onOffState`, `displayStatus`.

### BATTERY (0x80) — report 0x03

0–100 = battery %. `0xFF` = low battery sentinel (written as value=1, uiValue=`LOW`, warning logged). Sets `batteryLow=True` on all device types when level ≤ 20% or sentinel received.

### BASIC (0x20) — report 0x03

Legacy on/off. `0xFF` = on (99), `0x00` = off. Writes `dimLevel` and `onOffState`.

### MULTI_CHANNEL (0x60) — encapsulation 0x0D

Multi-channel frames are unwrapped transparently. The source endpoint is extracted and used to route the inner payload to the correct plugin device. The inner command class is then processed normally.

### WAKE_UP (0x84)

| Command | Bytes | Action |
|---|---|---|
| WAKE_UP_NOTIFICATION (0x07) | `84 07` | Touches `lastUpdate`; marks device online |
| WAKE_UP_INTERVAL_REPORT (0x06) | `84 06 b1 b2 b3 node` | Stores interval in `wakeUpInterval` state (seconds) |

---

## 13. Triggers and automations

Every state on the plugin device can be used as a trigger in Indigo.

| Use case | Trigger on |
|---|---|
| Motion alert | `motion` changes to True |
| Door opened | `contact` changes to True |
| Door closed | `contact` changes to False |
| Temperature threshold | `temperature` becomes greater than N |
| Low battery | `batteryLow` changes to True |
| Low battery (by level) | `batteryLevel` becomes less than 20 |
| Water leak | `waterLeak` changes to True |
| Smoke alarm | `smoke` changes to True |
| Lock locked | `lockState` changes to True |
| Lock unlocked | `lockState` changes to False |
| Scene button pressed | `lastScene` changes (any scene), or `lastSceneAction` becomes `pressed` |
| Device goes offline | `deviceOnline` changes to False |
| Device comes back online | `deviceOnline` changes to True |

The `onOffState` is set on all device types wherever meaningful, so standard Indigo triggers like "device turns on" also work.

---

## 14. Troubleshooting

### No states appear after creating the device

**Cause:** The sensor may not be sending the command class you expect, or debug logging will show what is arriving.

**Fix:** Enable debug logging and trigger the device. Look for `CC=0xXX` entries in the log — they confirm reports are arriving. If you see `Unhandled CC=0xXX`, that class is not yet parsed.

### Plugin device shows stale value after Indigo restart

**Cause:** Battery-powered devices only report on state change or scheduled wake-up. The plugin cannot poll them on demand.

**Fix:** Physically trigger the device to force a report. The `lastUpdate` timestamp shows how old the current value is.

### Dropdown shows no devices

**Cause:** No Indigo devices with a numeric Z-Wave address were found.

**Fix:** The dropdown lists devices that have a valid node ID in their address property. Ensure the native Indigo Z-Wave device is enabled and has been successfully included in the Z-Wave network.

### Lock events appear on the wrong device

**Cause:** NOTIFICATION ACCESS_CONTROL lock events (0x06) and DOOR_LOCK reports (0x62) both update the `lockState` state. If you have both a Lock sensor type device and another sensor type device on the same node, the lock events will fan out to all devices on the node but only update lock-relevant states.

**Fix:** For a lock, use the **Lock** sensor type. If you also want contact state from the same lock, use a second plugin device with **Contact** sensor type and the same native device.

### Scene controller shows wrong action

**Cause:** Some scene controllers number their scenes from 0; others from 1. The plugin reports the exact scene number from the hardware.

**Fix:** Enable debug logging and press the button — the log will show the exact `lastScene` value and `lastSceneAction`. Use those values in your trigger conditions.

### Temperature is showing in the wrong unit

**Fix:** Go to **Plugins → Universal Z-Wave Sensor → Configure...** and change Temperature unit. Existing stored values will update on the next report.

### Log is flooded with debug output

**Fix:** Disable **Enable debug logging** in Plugin Preferences.

---

## 15. Known limitations

| Limitation | Detail |
|---|---|
| Battery devices | Only report on state change or scheduled wake-up. Cannot be polled on demand. |
| METER_REPORT v3+ | Voltage (V) and current (A) now parsed via the v3 Scale2 bit. Power factor and other scale values above 5 are not decoded. |
| DOOR_LOCK user codes | User code management (add/delete users) is a send-side operation. This plugin only receives and decodes lock status reports. |
| S2 security | Indigo decrypts S2-encrypted frames before delivering them to plugins. The plugin only sees the decrypted payload — transparent. |
| Proprietary command classes | 0xF0 and above are manufacturer-specific. The plugin logs the raw bytes in `rawLastReport` but does not decode them. |

---

## 16. Changelog

| Version | Date | Summary |
|---|---|---|
| **5.0** | 03-May-2026 | DOOR_LOCK (CC 0x62) — lock mode, bolt/latch state (v2 door condition bitmask), last user; CENTRAL_SCENE (CC 0x5B) — scene number, key action (pressed/released/held/repeated), timestamp; NOTIFICATION ACCESS_CONTROL extended — manual/RF/keypad/auto lock and unlock ops with user ID extraction; NOTIFICATION HOME_SECURITY extended — intrusion (0x01/0x02) and glass break (0x05/0x06); METER gas (m3/ft3/ccf) and water (m3/ft3/gallons) meter types; SENSOR_MULTILEVEL extended — velocity, watts, voltage, current, air flow, VOC, soil moisture; Battery sensor type — dedicated sensorType with displayStatus and batteryLow flag; batteryLow state on all device types (True if ≤20% or 0xFF sentinel); 10 sensor types; 41 device states |
| **4.0** | 22-Mar-2026 | METER_REPORT v3 voltage (V) and current (A) — Scale2 bit (byte 2 bit 7) extracted and combined with 2-bit scale to form full 3-bit scale value; `voltage` and `current` device states now populated |
| **3.9** | 22-Mar-2026 | Startup banner in `__init__()` using raw constructor params (display_name, version, plugin_id); Info.plist standardised — PluginVersion key added (fixes blank version), IwsApiVersion, CFBundleURLTypes, GithubInfo added |
| **3.8** | 22-Mar-2026 | SENSOR_BINARY (CC 0x30) logging moved to DEBUG always — NOTIFICATION is the primary INFO source for motion events |
| **3.7** | 22-Mar-2026 | Log verbosity reduced — INFO only for report types matching the device's sensorType; secondary fan-out (e.g. temperature update on a Lux device) moved to DEBUG; HS_IDLE always DEBUG |
| **3.6** | 22-Mar-2026 | `_init_display_status()` — corrects stale displayStatus on plugin reload/restart |
| **3.5** | 22-Mar-2026 | displayStatus guards — motion events no longer overwrite displayStatus on Temperature/Lux/other non-motion device types |
| **3.4** | 22-Mar-2026 | Fixed NOTIFICATION event 0x08 (motion detected unknown location, not cleared); SENSOR_BINARY type 0x0C (motion) added to lookup |
| **3.3** | 22-Mar-2026 | Fixed serial API frame unwrapping — `subscribeToIncoming()` delivers the full Z-Wave serial frame; `_extract_node_and_bytes()` now strips the SOF+header to expose the command payload |
| **3.2** | 22-Mar-2026 | Simplified to single-path UI — always select native Indigo device from dropdown; manual node ID entry removed |
| **3.1** | 22-Mar-2026 | `indigo.zwave.subscribeToIncoming()` at startup so all Z-Wave bytes received regardless of node ownership; NOTIFICATION byte order auto-detection; native device picker added |
| **3.0** | 21-Mar-2026 | Multi-channel endpoint routing (CC 0x60); stale device detection; temperature unit preference; wake-up interval tracking; Simulate dialog stays open |
| **2.0** | 21-Mar-2026 | Removed known-device mirror path; plugin now uses raw Z-Wave bytes only |
| **1.0** | 20-Mar-2026 | Initial release |

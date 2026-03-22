# Universal Z-Wave Sensor — Indigo Plugin

**Version 3.1** | Indigo 2025.1 | Python 3.11

Allows any Z-Wave sensor to appear as a proper Indigo plugin device — including devices that Indigo does not natively recognise, and as a parallel companion to native Indigo devices for sensors that Indigo only partially supports.

---

## Why this exists

Indigo's built-in Z-Wave support handles recognised devices well, but there are two common gaps:

1. **Unrecognised hardware** — newer sensors, niche models, or devices not yet in Indigo's database appear as "Unknown Z-Wave Device" with no usable states
2. **Partially-supported hardware** — Indigo recognises the device and creates a native device, but omits sensor values it does not know about (temperature from a door sensor, humidity from a motion sensor, etc.)

The plugin solves both cases. It parses the raw Z-Wave command bytes directly via `zwaveCommandReceived()` and produces a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

---

## Features

- **Unrecognised Z-Wave nodes** — enter the node ID shown in Indigo's Z-Wave device list; plugin receives all raw bytes
- **Parallel mode** — if Indigo already has a native device on the node, tick *Parallel mode* and select the native device from a dropdown; the plugin receives all Z-Wave bytes alongside the native device via `indigo.zwave.subscribeToIncoming()`
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Multi-channel / endpoint support** — configure an optional endpoint ID per device; receives reports from multi-sensor devices that use Z-Wave endpoints (e.g. Aeotec 6-in-1)
- **Seven sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, generic
- **Correct icons** — thermometer, light sensor, motion, power, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, etc.
- **Temperature unit preference** — store and display all temperatures in degC or degF regardless of what the sensor reports; conversion applied automatically
- **Stale device detection** — configurable threshold (4–72 h); logs a warning and sets `deviceOnline=False` when a device goes silent; clears automatically when any report arrives
- **Wake-up interval tracking** — WAKE_UP_INTERVAL_REPORT stores the interval in the `wakeUpInterval` state; wake-up notifications mark the device as alive
- **Simulate Z-Wave Report** — menu item lets you feed raw hex bytes to any plugin device for end-to-end testing without needing real hardware; dialog stays open for iterative testing
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all state updates
- **98-test mock suite** — full test coverage without needing an Indigo server

---

## Sensor types and states

| Sensor type | Primary state | Additional states |
|---|---|---|
| Motion | `onOffState` (bool) | `motion`, `tamper`, `displayStatus` |
| Contact | `onOffState` (bool) | `contact`, `displayStatus` |
| Temperature | `temperature` (float, degC or degF) | `displayStatus` |
| Humidity | `humidity` (float, %) | `displayStatus` |
| Luminance | `luminance` (float, lux) | `displayStatus` |
| Energy | `watts` (float, W) | `kwh`, `displayStatus` |
| Generic | `onOffState` (bool) | `switchState`, `dimLevel`, `displayStatus` |

All device types also carry: `batteryLevel`, `waterLeak`, `smoke`, `coAlarm`, `co2Level`, `uvIndex`, `pressure`, `noise`, `lastUpdate`, `deviceOnline`, `wakeUpInterval`, `rawLastReport`

---

## Z-Wave command classes handled

| Hex | Class | What it decodes |
|---|---|---|
| `0x31` | SENSOR_MULTILEVEL | Temperature, humidity, luminance, CO2, UV, pressure, noise |
| `0x30` | SENSOR_BINARY | Motion, water, smoke, CO, tamper, door/window |
| `0x71` | NOTIFICATION v4+ | Motion, tamper, door/window, water, smoke, CO |
| `0x25` | SWITCH_BINARY | On/off relay |
| `0x26` | SWITCH_MULTILEVEL | Dimmers (0–99%) |
| `0x32` | METER | Power (W), energy (kWh) |
| `0x80` | BATTERY | Battery level %; 0xFF low warning |
| `0x20` | BASIC | Legacy on/off |
| `0x60` | MULTI_CHANNEL | Endpoint encapsulation — unwrapped transparently |
| `0x84` | WAKE_UP | Notification touches lastUpdate; interval stored in wakeUpInterval |

---

## Installation

1. Download or clone this repository
2. Double-click `UniversalZWaveSensor.indigoPlugin` to install
3. Enable the plugin from the Indigo Plugins menu

---

## Creating a device

### For an unrecognised node (Indigo has no native device)

1. **Plugins → Universal Z-Wave Sensor → New Device**
2. Leave *Parallel mode* unchecked
3. Enter the **Z-Wave Node ID** (shown in Indigo's Z-Wave device list)
4. Choose the **Sensor Type** (sets icon and displayStatus format)
5. *(Optional)* Enter an **Endpoint ID** for multi-channel devices

### For a node Indigo already knows (Parallel mode)

Use this when Indigo already has a native device for the sensor but is missing some values — for example, a door/window sensor where Indigo provides the contact state but not the temperature or humidity the device also sends.

1. **Plugins → Universal Z-Wave Sensor → New Device**
2. Tick **Parallel mode — native Indigo device exists on this node**
3. Select the existing native Indigo device from the dropdown — node ID is read automatically
4. Choose the **Sensor Type** for the value you want to capture (e.g. Temperature Sensor)
5. *(Optional)* Enter an **Endpoint ID** if needed

You can create multiple parallel plugin devices on the same node (one for temperature, one for humidity, etc.). The node ID is populated automatically from the selected native device.

> **Naming tip:** Name parallel devices to make their temporary nature clear, e.g. `Bathroom Door Sensor (Temp)` or `Bathroom Door Sensor (Bridge)`. When Indigo adds native support for the missing values, delete the plugin devices and update any triggers or action groups that reference them — a one-time job.

The plugin receives all Z-Wave bytes via `indigo.zwave.subscribeToIncoming()`, which is called at startup. Both the native Indigo device and the plugin device receive every report from the node simultaneously.

---

## Plugin preferences

| Setting | Default | Description |
|---|---|---|
| Enable debug logging | Off | Logs raw Z-Wave byte sequences and all state updates |
| Log unknown command classes | On | Writes unrecognised report bytes to `rawLastReport` state and Indigo log |
| Temperature unit | degC | All temperature reports converted to this unit before storing |
| Enable stale device detection | On | Warns when a device has not reported within the threshold |
| Stale threshold | 24 hours | How long without a report before a device is considered offline |

---

## Simulate Z-Wave Report

**Plugins → Universal Z-Wave Sensor → Simulate Z-Wave Report...**

Select a plugin device, enter space-separated hex bytes, and click **Send**. The bytes are fed directly into the parser as if real hardware had sent them. The dialog stays open so you can send multiple sequences without reopening it.

| Byte sequence | What it simulates |
|---|---|
| `31 05 01 22 00 D7` | Temperature 21.5 degC |
| `71 05 00 00 00 FF 07 07 00` | Motion detected (NOTIFICATION) |
| `71 05 00 00 00 FF 07 08 00` | Motion cleared |
| `71 05 00 00 00 FF 06 16 00` | Door opened |
| `71 05 00 00 00 FF 06 17 00` | Door closed |
| `80 03 55` | Battery 85% |
| `80 03 FF` | Battery LOW warning |
| `84 07` | Wake-up notification |
| `84 06 00 01 2C 6F` | Wake-up interval = 300 s (5 min) |
| `60 0D 00 01 31 05 01 22 00 D7` | Multi-channel ep 1: temperature 21.5 degC |

---

## Stale device detection

The plugin checks all plugin devices every 60 seconds. If a device's `lastUpdate` is older than the configured threshold:

- A warning is logged: `Sensor: No report for 26.3h (threshold 24h) — may be offline or out of range`
- `deviceOnline` state is set to `False` (uiValue `offline`)
- The warning is only logged **once** — no repeated entries

When any Z-Wave report arrives from the device, `deviceOnline` is immediately restored to `True` and `Back online (report received)` is logged.

> **Tip:** Battery devices typically report every few hours to days. Set the threshold generously — 48 or 72 hours is reasonable for weekly-reporting sensors.

---

## Multi-channel devices

Some multi-sensors (e.g. Aeotec MultiSensor 6) use Z-Wave multi-channel addressing: each sensor type is exposed as a separate endpoint on the same node.

**Setup for a 3-in-1 sensor (motion ep 1, temperature ep 2, luminance ep 3) on node 42:**

| Plugin device | Node ID | Endpoint ID | Sensor Type |
|---|---|---|---|
| Hall Motion | 42 | 1 | Motion Sensor |
| Hall Temperature | 42 | 2 | Temperature Sensor |
| Hall Luminance | 42 | 3 | Luminance Sensor |

Leave **Endpoint ID** blank (or set to `0`) to accept reports from all endpoints on the node.

---

## Limitations

| Item | Notes |
|---|---|
| Battery devices | Only report on state change or wake-up — cannot be polled on demand |
| METER_REPORT v3+ | Voltage (V) and current (A) require extended scale byte — not yet parsed |
| S2 security | Indigo decrypts S2 before delivery — transparent to the plugin |
| Proprietary command classes | 0xF0+ manufacturer-specific bytes logged raw but not decoded |

---

## Running the tests

```bash
cd "UniversalZWaveSensor.indigoPlugin/Contents/Server Plugin"
python3 test_plugin.py -v
```

No Indigo installation required — `indigo` is fully mocked. All 98 tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| 3.1 | 22-Mar-2026 | Parallel mode: plugin devices can coexist alongside native Indigo devices on the same node; `indigo.zwave.subscribeToIncoming()` called at startup so all Z-Wave bytes are received regardless of node ownership; NOTIFICATION byte order auto-detection (spec order and reversed-order hardware both handled); 98 tests |
| 3.0 | 21-Mar-2026 | Multi-channel endpoint routing; stale device detection; temperature unit preference (degC/degF); wake-up interval tracking; simulate dialog stays open; .gitignore added |
| 2.2 | 21-Mar-2026 | Added "Simulate Z-Wave Report" menu item for end-to-end testing without unknown hardware |
| 2.0 | 21-Mar-2026 | Removed known-device mirror path (subscribeToChanges); plugin now uses raw Z-Wave bytes only |
| 1.0 | 20-Mar-2026 | Initial release |

---

## Licence

MIT — free to use, modify, and distribute.

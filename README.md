# Universal Z-Wave Sensor — Indigo Plugin

**Version 3.0** | Indigo 2025.1 | Python 3.11

Allows any Z-Wave sensor to appear as a proper Indigo plugin device — specifically devices that Indigo does **not** natively recognise — without waiting for official support.

---

## Why this exists

Indigo's built-in Z-Wave support handles recognised devices perfectly. For everything else — newer hardware, niche sensors, devices not yet in Indigo's database — the plugin takes over: it parses the raw Z-Wave command bytes directly via `zwaveCommandReceived()` and produces a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

> **Note:** This plugin is for *unknown* devices only. If Indigo already creates a native device for your sensor, use that — it is first-class and needs no wrapper.

---

## Features

- **Any unrecognised Z-Wave node** — enter the node ID shown in Indigo's Z-Wave device list
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Multi-channel / endpoint support** — configure an optional endpoint ID per device; receives reports from multi-sensor devices that use Z-Wave endpoints (e.g. Aeotec 6-in-1)
- **Seven sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, generic
- **Correct icons** — thermometer, light sensor, motion, power, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, etc.
- **Temperature unit preference** — store and display all temperatures in degC or degF regardless of what the sensor reports; conversion applied automatically
- **Stale device detection** — configurable threshold (4–72 h); logs a warning and sets `deviceOnline=False` when a device goes silent; clears automatically when any report arrives
- **Wake-up interval tracking** — WAKE_UP_INTERVAL_REPORT stores the interval in the `wakeUpInterval` state; wake-up notifications mark the device as alive
- **Simulate Z-Wave Report** — menu item lets you feed raw hex bytes to any plugin device for end-to-end testing without needing unknown hardware; dialog stays open for iterative testing
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all state updates
- **80-test mock suite** — full test coverage without needing an Indigo server

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

1. **Plugins → Universal Z-Wave Sensor → New Device**
2. Enter the **Z-Wave Node ID** (shown in Indigo's Z-Wave device list)
3. Choose the **Sensor Type** (sets icon and displayStatus format)
4. *(Optional)* Enter an **Endpoint ID** if this is a multi-channel device and you want this plugin device to respond only to a specific endpoint (e.g. `1`, `2`). Leave blank to accept all endpoints.

The plugin receives raw Z-Wave reports from that node automatically. If the device sends multiple sensor types (e.g. motion + temperature + luminance), create one plugin device per reading and assign each the appropriate sensor type. For multi-channel devices, create one plugin device per endpoint and set the endpoint ID on each.

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
| `71 05 00 00 00 07 FF 07 00` | Motion detected |
| `71 05 00 00 00 07 00 08 00` | Motion cleared |
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
| Known devices | If Indigo already recognises your device, use the native Indigo device — this plugin is not needed |
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

No Indigo installation required — `indigo` is fully mocked. All 80 tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| 3.0 | 21-Mar-2026 | Multi-channel endpoint routing; stale device detection; temperature unit preference (degC/degF); wake-up interval tracking; simulate dialog stays open; .gitignore added |
| 2.2 | 21-Mar-2026 | Added "Simulate Z-Wave Report" menu item for end-to-end testing without unknown hardware |
| 2.1 | 21-Mar-2026 | validateDeviceConfigUi warns if node already has native Indigo devices (zwaveCommandReceived won't fire for it) |
| 2.0 | 21-Mar-2026 | Removed known-device mirror path (subscribeToChanges); plugin now purely for unrecognised devices via raw Z-Wave bytes |
| 1.5 | 21-Mar-2026 | Fixed `_handle_multilevel` using SensorOn for all types; removed unreachable V/A meter entries |
| 1.4 | 21-Mar-2026 | Correct icons for temperature (thermometer), humidity, luminance across all code paths |
| 1.3 | 21-Mar-2026 | Initial state sync on deviceStartComm — no stale values after plugin reload |
| 1.2 | 21-Mar-2026 | `sensorValue` fallback for temperature blocked without sourceDeviceId to prevent lux/temp mix-up |
| 1.1 | 20-Mar-2026 | Feedback loop fix: skip own plugin devices in deviceUpdated |
| 1.0 | 20-Mar-2026 | Initial release |

---

## Licence

MIT — free to use, modify, and distribute.

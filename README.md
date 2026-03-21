# Universal Z-Wave Sensor — Indigo Plugin

**Version 2.2** | Indigo 2025.1 | Python 3.11

Allows any Z-Wave sensor to appear as a proper Indigo plugin device — specifically devices that Indigo does **not** natively recognise — without waiting for official support.

---

## Why this exists

Indigo's built-in Z-Wave support handles recognised devices perfectly. For everything else — newer hardware, niche sensors, devices not yet in Indigo's database — the plugin takes over: it parses the raw Z-Wave command bytes directly via `zwaveCommandReceived()` and produces a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

> **Note:** This plugin is for *unknown* devices only. If Indigo already creates a native device for your sensor, use that — it is first-class and needs no wrapper.

---

## Features

- **Any unrecognised Z-Wave node** — enter the node ID shown in Indigo's Z-Wave device list
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Seven sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, generic
- **Correct icons** — thermometer, light sensor, motion, power, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, etc.
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all state updates
- **58-test mock suite** — full test coverage without needing an Indigo server

---

## Sensor types and states

| Sensor type | Primary state | Additional states |
|---|---|---|
| Motion | `onOffState` (bool) | `motion`, `tamper`, `displayStatus` |
| Contact | `onOffState` (bool) | `contact`, `displayStatus` |
| Temperature | `temperature` (float, degC) | `displayStatus` |
| Humidity | `humidity` (float, %) | `displayStatus` |
| Luminance | `luminance` (float, lux) | `displayStatus` |
| Energy | `watts` (float, W) | `kwh`, `displayStatus` |
| Generic | `onOffState` (bool) | `switchState`, `dimLevel`, `displayStatus` |

All device types also carry: `batteryLevel`, `waterLeak`, `smoke`, `coAlarm`, `co2Level`, `uvIndex`, `pressure`, `noise`, `lastUpdate`, `rawLastReport`

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
| `0x84` | WAKE_UP | Logged (no state written) |

---

## Installation

1. Download or clone this repository
2. Double-click `UniversalZWaveSensor.indigoPlugin` to install
3. Enable the plugin from the Indigo Plugins menu

---

## Creating a device

1. **Plugins → Universal Z-Wave Sensor → Create Device**
2. Enter the **Z-Wave Node ID** (shown in Indigo's Z-Wave device list)
3. Choose the **Sensor Type** (sets icon and displayStatus format)

The plugin receives raw Z-Wave reports from that node automatically. If the device sends multiple sensor types (e.g. motion + temperature + luminance), create one plugin device per reading and assign each the appropriate sensor type.

---

## Plugin preferences

| Setting | Default | Description |
|---|---|---|
| Enable debug logging | Off | Logs raw Z-Wave byte sequences and all state updates |
| Log unknown command classes | On | Writes unrecognised report bytes to `rawLastReport` state and Indigo log |

---

## Limitations

| Item | Notes |
|---|---|
| Known devices | If Indigo already recognises your device, use the native Indigo device — this plugin is not needed |
| Battery devices | Only report on state change or wake-up — cannot be polled on demand |
| Multi-channel devices | Endpoint routing not yet implemented |
| METER_REPORT v3+ | Voltage (V) and current (A) require extended scale byte — not yet parsed |
| S2 security | Indigo decrypts S2 before delivery — transparent to the plugin |
| Proprietary command classes | 0xF0+ manufacturer-specific bytes logged raw but not decoded |

---

## Running the tests

```bash
cd "UniversalZWaveSensor.indigoPlugin/Contents/Server Plugin"
python3 test_plugin.py -v
```

No Indigo installation required — `indigo` is fully mocked. All 58 tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
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

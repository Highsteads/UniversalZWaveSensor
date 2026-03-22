# Universal Z-Wave Sensor — Indigo Plugin

**Version 3.3** | Indigo 2025.1 | Python 3.11

Creates companion plugin devices alongside your existing Indigo Z-Wave devices, exposing sensor values that Indigo does not capture natively — temperature, humidity, luminance, contact state, and more.

---

## Why this exists

When you include a Z-Wave sensor in Indigo, Indigo creates a native device for it based on what it recognises. That works well for the values Indigo knows about. But many sensors send additional data that Indigo ignores — a door/window sensor that also reports temperature, a multi-sensor where Indigo captures motion but not humidity or luminance, a sensor model that Indigo lists but only partially supports.

This plugin fills that gap. You select the existing native Indigo device, choose the sensor type you want to capture, and the plugin creates a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

The plugin also provides a **Simulate Z-Wave Report** tool — useful for sending raw Z-Wave byte captures to Mat and Jay (Indigo's authors) when a sensor is behaving unexpectedly, so they can add or improve native support.

---

## Features

- **Select from your existing Indigo devices** — dropdown lists all native Z-Wave devices; node ID is read automatically
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Multi-channel / endpoint support** — optional endpoint ID per device for multi-channel sensors (e.g. Aeotec 6-in-1)
- **Seven sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, generic
- **Correct icons** — thermometer, light sensor, motion, power, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, etc.
- **Temperature unit preference** — store and display all temperatures in degC or degF regardless of what the sensor reports; conversion applied automatically
- **Stale device detection** — configurable threshold (4–72 h); logs a warning and sets `deviceOnline=False` when a device goes silent; clears automatically when any report arrives
- **Wake-up interval tracking** — WAKE_UP_INTERVAL_REPORT stores the interval in the `wakeUpInterval` state; wake-up notifications mark the device as alive
- **Simulate Z-Wave Report** — menu item lets you feed raw hex bytes to any plugin device for end-to-end testing; dialog stays open for iterative testing
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all state updates
- **96-test mock suite** — full test coverage without needing an Indigo server

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

1. **Devices → New Device**
2. Set Type to **Universal Z-Wave Sensor**, Model to **Universal Z-Wave Sensor**
3. Click **Edit Device Settings**
4. Select the **Native Indigo Z-Wave Device** from the dropdown — the node ID is read automatically
5. Choose the **Sensor Type** for the value you want to capture (e.g. Temperature Sensor)
6. *(Optional)* Enter an **Endpoint ID** for multi-channel devices

For a multi-sensor (e.g. door sensor that also sends temperature and humidity), create one plugin device per sensor type and select the same native device for each.

> **Naming tip:** Name plugin devices to reflect what they add, e.g. `Bathroom Door (Temp)` or `Hall PIR (Humidity)`. When Indigo adds native support for those values, delete the plugin devices and update any triggers or action groups — a one-time job.

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

| Plugin device | Sensor Type | Endpoint ID |
|---|---|---|
| Hall Motion | Motion Sensor | 1 |
| Hall Temperature | Temperature Sensor | 2 |
| Hall Luminance | Luminance Sensor | 3 |

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

No Indigo installation required — `indigo` is fully mocked. All 96 tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| 3.3 | 22-Mar-2026 | Fixed serial API frame unwrapping — subscribeToIncoming() delivers full Z-Wave serial frame; _extract_node_and_bytes() now strips SOF+header to expose command payload; 96 tests |
| 3.2 | 22-Mar-2026 | Simplified to single-path UI — always select native Indigo device from dropdown; manual node ID entry removed |
| 3.1 | 22-Mar-2026 | `indigo.zwave.subscribeToIncoming()` at startup so all Z-Wave bytes received regardless of node ownership; NOTIFICATION byte order auto-detection; native device picker added |
| 3.0 | 21-Mar-2026 | Multi-channel endpoint routing; stale device detection; temperature unit preference (degC/degF); wake-up interval tracking; simulate dialog stays open |
| 2.0 | 21-Mar-2026 | Removed known-device mirror path; plugin now uses raw Z-Wave bytes only |
| 1.0 | 20-Mar-2026 | Initial release |

---

## Licence

MIT — free to use, modify, and distribute.

# Universal Z-Wave Sensor — Indigo Plugin

**Version 1.5** | Indigo 2025.1 | Python 3.11

Allows any Z-Wave sensor to appear as a proper Indigo plugin device — including devices that Indigo does not natively recognise — without waiting for official support.

---

## Why this exists

Indigo's built-in Z-Wave support is excellent for devices it knows about, but there are always newer or less-common sensors that don't appear correctly in the device list. This plugin bridges that gap using two complementary paths:

- **Known devices** — mirrors states from Indigo's own native Z-Wave devices using `subscribeToChanges()`. No raw byte parsing needed; it just reads whatever Indigo already decoded.
- **Unknown devices** — parses raw Z-Wave command bytes directly via `zwaveCommandReceived()`. The plugin decodes the standard command classes so even unrecognised hardware works immediately.

Both paths produce identical, properly-typed Indigo plugin devices that can be used in triggers, control pages, and action groups exactly like any native device.

---

## Features

- **Any Z-Wave node** — enter the node ID shown in Indigo's Z-Wave device list; works for any paired device
- **Multiple plugin devices per node** — one physical multi-sensor (motion + temperature + luminance) creates three separate plugin devices, matching Indigo's own approach
- **Source Device filter** — each plugin device targets one specific Indigo source device, preventing cross-contamination between sensor types on the same node
- **Seven sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, generic
- **Correct icons** — thermometer, light sensor, motion, power, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, etc.
- **Initial state sync** — on plugin startup or reload, each device immediately reads its current value from the source device (no stale readings after restart)
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all mirrored state changes
- **82-test mock suite** — full test coverage without needing an Indigo server

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
4. Select the **Source Indigo Device** from the dropdown (required for known multi-sensors — ensures each plugin device only mirrors from its specific source)
5. Leave Source blank for unknown devices — raw Z-Wave path will be used automatically

### Multi-sensor example (Neo NEOEMS02Z)

Indigo creates three separate native devices for this sensor (motion, temperature, luminance), all with the same node address. Create three plugin devices:

| Plugin device name | Node ID | Sensor Type | Source Indigo Device |
|---|---|---|---|
| Front Door Motion | 223 | Motion | Front Door Motion |
| Front Door Temperature | 223 | Temperature | Front Door Temperature |
| Front Door Luminance | 223 | Luminance | Front Door Luminance |

---

## Plugin preferences

| Setting | Default | Description |
|---|---|---|
| Enable debug logging | Off | Logs raw Z-Wave byte sequences and all state mirrors |
| Log unknown command classes | On | Writes unrecognised report bytes to `rawLastReport` state and Indigo log |

---

## Limitations

| Item | Notes |
|---|---|
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

No Indigo installation required — `indigo` is fully mocked. All 82 tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| 1.5 | 21-Mar-2026 | Fixed `_handle_multilevel` using SensorOn for all types; removed unreachable V/A meter entries |
| 1.4 | 21-Mar-2026 | Correct icons for temperature (thermometer), humidity, luminance across all code paths |
| 1.3 | 21-Mar-2026 | Initial state sync on deviceStartComm — no stale values after plugin reload |
| 1.2 | 21-Mar-2026 | `sensorValue` fallback for temperature blocked without sourceDeviceId to prevent lux/temp mix-up |
| 1.1 | 20-Mar-2026 | Feedback loop fix: skip own plugin devices in deviceUpdated |
| 1.0 | 20-Mar-2026 | Initial release |

---

## Licence

MIT — free to use, modify, and distribute.

# Universal Z-Wave Sensor — Indigo Plugin

**Version 5.0** | Indigo 2025.1+ | Python 3.11+

Creates companion plugin devices alongside your existing Indigo Z-Wave devices, exposing sensor values that Indigo does not capture natively — temperature, humidity, luminance, contact state, lock state, scene controller events, and more.

---

## Why this exists

When you include a Z-Wave sensor in Indigo, Indigo creates a native device for it based on what it recognises. That works well for the values Indigo knows about. But many sensors send additional data that Indigo ignores — a door/window sensor that also reports temperature, a multi-sensor where Indigo captures motion but not humidity or luminance, a lock that sends detailed bolt/latch state, a scene controller Indigo doesn't support at all.

This plugin fills that gap. You select the existing native Indigo device, choose the sensor type you want to capture, and the plugin creates a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

The plugin also provides a **Simulate Z-Wave Report** tool — useful for sending raw Z-Wave byte captures to Matt and Jay (Indigo's authors) when a sensor is behaving unexpectedly, so they can add or improve native support.

---

## Features

- **Select from your existing Indigo devices** — dropdown lists all native Z-Wave devices; node ID is read automatically
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Multi-channel / endpoint support** — optional endpoint ID per device for multi-channel sensors (e.g. Aeotec 6-in-1)
- **Ten sensor types** — motion, contact, temperature, humidity, luminance, energy monitor, battery, lock, scene controller, generic
- **Correct icons** — thermometer, light sensor, motion, power, lock, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, `locked / unlocked`, `S1 pressed`, etc.
- **Temperature unit preference** — store and display all temperatures in degC or degF regardless of what the sensor reports; conversion applied automatically
- **Battery sensor type** — dedicated battery device with `batteryLow` flag; all device types also carry `batteryLevel` and `batteryLow` states
- **Lock support** — DOOR_LOCK_OPERATION_REPORT decodes lock mode, bolt state, latch state, and last user ID; NOTIFICATION ACCESS_CONTROL events for keypad/RF/manual lock and unlock
- **Scene controller** — CENTRAL_SCENE_NOTIFICATION decodes scene number, key action (pressed/released/held/repeated), and timestamp
- **Stale device detection** — configurable threshold (4–72 h); logs a warning and sets `deviceOnline=False` when a device goes silent; clears automatically when any report arrives
- **Wake-up interval tracking** — WAKE_UP_INTERVAL_REPORT stores the interval in the `wakeUpInterval` state; wake-up notifications mark the device as alive
- **Simulate Z-Wave Report** — menu item lets you feed raw hex bytes to any plugin device for end-to-end testing; dialog stays open for iterative testing
- **Debug logging** — toggleable; logs raw Z-Wave bytes and all state updates
- **Mock test suite** — full test coverage without needing an Indigo server

---

## Sensor types and states

| Sensor type | Primary state | Additional states |
|---|---|---|
| Motion | `onOffState` (bool) | `motion`, `tamper`, `displayStatus` |
| Contact | `onOffState` (bool) | `contact`, `displayStatus` |
| Temperature | `temperature` (float, degC or degF) | `displayStatus` |
| Humidity | `humidity` (float, %) | `displayStatus` |
| Luminance | `luminance` (float, lux) | `displayStatus` |
| Energy | `watts` (float, W) | `kwh`, `voltage`, `current`, `displayStatus` |
| Battery | `batteryLevel` (int, %) | `batteryLow`, `onOffState`, `displayStatus` |
| Lock | `lockState` (bool) | `lockMode`, `boltState`, `latchState`, `lastUser`, `onOffState`, `displayStatus` |
| Scene Controller | `lastScene` (int) | `lastSceneAction`, `sceneTimestamp`, `onOffState`, `displayStatus` |
| Generic | `onOffState` (bool) | `switchState`, `dimLevel`, `displayStatus` |

All device types also carry: `batteryLevel`, `batteryLow`, `waterLeak`, `smoke`, `coAlarm`, `co2Level`, `uvIndex`, `pressure`, `noise`, `velocity`, `airFlow`, `voc`, `soilMoisture`, `gasCubicMeters`, `waterCubicMeters`, `lastUpdate`, `deviceOnline`, `wakeUpInterval`, `rawLastReport`

---

## Z-Wave command classes handled

| Hex | Class | What it decodes |
|---|---|---|
| `0x31` | SENSOR_MULTILEVEL | Temperature, humidity, luminance, CO2, UV, pressure, noise, velocity, power (W), voltage (V), current (A), air flow, VOC, soil moisture |
| `0x30` | SENSOR_BINARY | Motion, water, smoke, CO, tamper, door/window |
| `0x71` | NOTIFICATION v4+ | Motion, tamper, intrusion, glass break, door/window, water, smoke, CO, lock/unlock ops (manual/RF/keypad/auto) |
| `0x62` | DOOR_LOCK | Lock mode, bolt state, latch state (v2+), last user |
| `0x5B` | CENTRAL_SCENE | Scene number, key action (pressed/released/held/repeated), sequence number |
| `0x25` | SWITCH_BINARY | On/off relay |
| `0x26` | SWITCH_MULTILEVEL | Dimmers (0–99%) |
| `0x32` | METER | Power (W), energy (kWh/kVAh), voltage (V, Scale2), current (A, Scale2), gas (m3/ft3/ccf), water (m3/ft3/gallons) |
| `0x80` | BATTERY | Battery level %; 0xFF low warning |
| `0x20` | BASIC | Legacy on/off |
| `0x60` | MULTI_CHANNEL | Endpoint encapsulation — unwrapped transparently |
| `0x84` | WAKE_UP | Notification touches lastUpdate; interval stored in wakeUpInterval |

---

## Installation

1. Go to the [Releases page](https://github.com/Highsteads/UniversalZWaveSensor/releases) and download `UniversalZWaveSensor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `UniversalZWaveSensor.indigoPlugin`
3. Double-click `UniversalZWaveSensor.indigoPlugin` — Indigo will install it automatically
4. Enable the plugin from the Indigo Plugins menu

---

## Upgrading from a previous version

Existing plugin devices upgrade automatically. When Indigo loads the new plugin, it calls `device.stateListOrDisplayStateIdChanged()` on each device, which adds any new states with default values. No manual steps are needed. Your existing triggers and action groups continue to work unchanged.

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
| Temperature unit | degC | Choose degC or degF — all temperature reports are converted to this unit before storing, regardless of what the sensor reports |
| Enable stale device detection | On | Warns when a device has not reported within the threshold |
| Stale threshold | 24 hours | How long without a report before a device is considered offline |

---

## Simulate Z-Wave Report

**Plugins → Universal Z-Wave Sensor → Simulate Z-Wave Report...**

Select a plugin device, enter space-separated hex bytes, and click **Send**. The bytes are fed directly into the parser as if real hardware had sent them. The dialog stays open so you can send multiple sequences without reopening it.

| Byte sequence | What it simulates |
|---|---|
| `31 05 01 22 00 D7` | Temperature 21.5 degC |
| `31 05 03 0A 01 C2` | Luminance 450 lux |
| `31 05 05 01 41` | Humidity 65% |
| `71 05 00 00 00 FF 07 07 00` | Motion detected (NOTIFICATION) |
| `71 05 00 00 00 FF 07 08 00` | Motion cleared |
| `71 05 00 00 00 FF 06 16 00` | Door opened |
| `71 05 00 00 00 FF 06 17 00` | Door closed |
| `71 05 00 00 00 FF 06 01 01 00` | Manual lock (user 0) |
| `71 05 00 00 00 FF 06 06 02 05` | Keypad lock (user 5) |
| `62 03 FF 00 00 FE` | Door lock — locked (v2, bolt locked, latch closed) |
| `62 03 00 00 00 FD` | Door lock — unlocked (v2, bolt unlocked, latch open) |
| `5B 03 01 00 01` | Scene 1, key pressed |
| `5B 03 02 01 01` | Scene 1, key released |
| `5B 03 03 02 02` | Scene 2, key held |
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
| METER_REPORT v3+ | Voltage (V) and current (A) parsed using the Scale2 bit (byte 2 bit 7); power factor and other higher scale values not decoded |
| S2 security | Indigo decrypts S2 before delivery — transparent to the plugin |
| Proprietary command classes | 0xF0+ manufacturer-specific bytes logged raw but not decoded |

---

## Running the tests

```bash
cd "UniversalZWaveSensor.indigoPlugin/Contents/Server Plugin"
python3 test_plugin.py -v
```

No Indigo installation required — `indigo` is fully mocked. All tests should pass.

---

## Changelog

| Version | Date | Changes |
|---|---|---|
| 5.0 | 03-May-2026 | DOOR_LOCK (CC 0x62) — lock mode, bolt/latch state (v2 door condition bitmask), last user; CENTRAL_SCENE (CC 0x5B) — scene number, key action (pressed/released/held/repeated), timestamp; NOTIFICATION ACCESS_CONTROL extended — manual/RF/keypad/auto lock and unlock ops with user ID extraction; NOTIFICATION HOME_SECURITY extended — intrusion (0x01/0x02) and glass break (0x05/0x06); METER gas (m3/ft3/ccf) and water (m3/ft3/gallons) meter types; SENSOR_MULTILEVEL extended — velocity, watts, voltage, current, air flow, VOC, soil moisture; Battery sensor type — dedicated sensorType with displayStatus and batteryLow flag; batteryLow state on all device types (True if ≤20% or 0xFF sentinel); 10 sensor types; 41 device states |
| 4.0 | 22-Mar-2026 | METER_REPORT v3 voltage (V) and current (A) — Scale2 bit (byte 2 bit 7) now extracted and combined with 2-bit scale to form full 3-bit scale value |
| 3.9 | 22-Mar-2026 | Startup banner in `__init__()` using raw constructor params; Info.plist standardised (PluginVersion key added — fixes blank version, IwsApiVersion, CFBundleURLTypes, GithubInfo) |
| 3.8 | 22-Mar-2026 | SENSOR_BINARY (CC 0x30) logging moved to DEBUG always — NOTIFICATION is the primary INFO source for motion events |
| 3.7 | 22-Mar-2026 | Log verbosity reduced — INFO only for report types matching device sensorType; secondary fan-out and HS_IDLE moved to DEBUG |
| 3.6 | 22-Mar-2026 | Startup displayStatus initialisation — _init_display_status() called in deviceStartComm(); corrects stale values (e.g. "detected" on Temperature device) immediately on plugin reload |
| 3.5 | 22-Mar-2026 | displayStatus guard per sensorType — motion/NOTIFICATION/SENSOR_BINARY reports no longer overwrite displayStatus on Temperature or Lux devices sharing the same node |
| 3.4 | 22-Mar-2026 | NOTIFICATION event 0x08 = motion DETECTED (not cleared); SENSOR_BINARY type 0x0C added to lookup table |
| 3.3 | 22-Mar-2026 | Fixed serial API frame unwrapping — subscribeToIncoming() delivers full Z-Wave serial frame; _extract_node_and_bytes() now strips SOF+header to expose command payload |
| 3.2 | 22-Mar-2026 | Simplified to single-path UI — always select native Indigo device from dropdown; manual node ID entry removed |
| 3.1 | 22-Mar-2026 | `indigo.zwave.subscribeToIncoming()` at startup so all Z-Wave bytes received regardless of node ownership; NOTIFICATION byte order auto-detection; native device picker added |
| 3.0 | 21-Mar-2026 | Multi-channel endpoint routing; stale device detection; temperature unit preference (degC/degF); wake-up interval tracking; simulate dialog stays open |
| 2.0 | 21-Mar-2026 | Removed known-device mirror path; plugin now uses raw Z-Wave bytes only |
| 1.0 | 20-Mar-2026 | Initial release |

---

## Licence

MIT — free to use, modify, and distribute.

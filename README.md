# Universal Z-Wave Sensor — Indigo Plugin

**Version 5.13** | Indigo 2025.2+ | Python 3.13+

Creates companion plugin devices alongside your existing Indigo Z-Wave devices, exposing sensor values that Indigo does not capture natively — temperature, humidity, luminance, contact state, lock state, scene controller events, and more.

---

## Why this exists

When you include a Z-Wave sensor in Indigo, Indigo creates a native device for it based on what it recognises. That works well for the Devices Indigo knows about. But many new Devices that are not supported by Indigo can now be included with this plugin until it becomes included into Indigo.

This plugin fills that gap. You select the existing native Indigo device, choose the sensor type you want to capture, and the plugin creates a properly-typed Indigo device that works in triggers, control pages, and action groups exactly like any native device.

The plugin also provides a **Simulate Z-Wave Report** tool — useful for sending raw Z-Wave byte captures to Matt and Jay (Indigo's authors) when a sensor is behaving unexpectedly, so they can add or improve native support.

---

## Features

- **Select from your existing Indigo devices** — the dropdown lists every native Z-Wave device, and reads the node ID for you
- **Multiple plugin devices per node** — one physical multi-sensor creates separate plugin devices per reading type (motion, temperature, luminance), each assigned the appropriate sensor type
- **Multi-channel / endpoint support** — optional endpoint ID per device for multi-channel sensors (e.g. Aeotec 6-in-1)
- **Eleven device types** — motion, contact, temperature, humidity, luminance, energy monitor, battery, lock, scene controller, plug/relay, generic
- **Correct icons** — thermometer, light sensor, motion, power, lock, and generic sensor icons set automatically
- **displayStatus** — device list shows meaningful values: `detected / clear`, `open / closed`, `21.5 degC`, `450 lux`, `locked / unlocked`, `S1 pressed`, etc.
- **Temperature unit preference** — store and show every temperature in degC or degF whatever the sensor reports, with the conversion done for you
- **Battery sensor type** — a dedicated battery device with a `batteryLow` flag, and every battery-powered device type also carries `battery` (percentage) and `batteryLow` states
- **Lock support** — DOOR_LOCK_OPERATION_REPORT decodes lock mode, bolt state, latch state and last user ID, and NOTIFICATION ACCESS_CONTROL covers keypad, RF and manual lock and unlock
- **Scene controller** — CENTRAL_SCENE_NOTIFICATION decodes scene number, key action (pressed/released/held/repeated), and timestamp
- **Stale device detection** — set a threshold between 4 hours and 14 days. When a device falls silent the plugin logs a warning and sets `deviceOnline=False`, then clears it the moment any report arrives
- **Configurable low-battery warning** — set the percentage at which the `batteryLow` flag trips (10–30%, default 20%)
- **Wake-up interval tracking** — WAKE_UP_INTERVAL_REPORT stores the interval in the `wakeUpInterval` state, and a wake-up notification marks the device alive
- **Simulate Z-Wave Report** — a menu item that feeds raw hex bytes to any plugin device for end-to-end testing. The dialog stays open so you can keep trying
- **Run Parser Self-Test** — menu item replays a set of documented sample reports through the real parsers and logs a pass/fail line for each, so you can confirm decoding works without any hardware
- **Show Status** — menu item logs a one-glance table of every monitored device: node, sensor type, online/stale, and last update time
- **Generate Indigo Support Report** — one menu click dumps manufacturer ID, product type and ID, supported command classes, and every device property and state to the Indigo log, laid out ready to paste into the Indigo forum when asking for native support
- **Debug logging** — turn it on to log the raw Z-Wave bytes and every state update
- **Mock test suite** — 182 tests, full coverage without needing an Indigo server

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
| Battery | `battery` (int, %) | `batteryLow`, `onOffState`, `displayStatus` |
| Plug / Relay | `onOffState` (bool) | `switchState`, `watts`, `kwh`, `voltage`, `current`, `deviceOnline`, `displayStatus` |
| Lock | `lockState` (bool) | `lockMode`, `boltState`, `latchState`, `lastUser`, `onOffState`, `displayStatus` |
| Scene Controller | `lastScene` (int) | `lastSceneAction`, `sceneTimestamp`, `onOffState`, `displayStatus` |
| Generic | `onOffState` (bool) | `switchState`, `dimLevel`, `displayStatus` |

All sensor device types also carry: `battery`, `batteryLow`, `waterLeak`, `smoke`, `coAlarm`, `co2Level`, `uvIndex`, `pressure`, `noise`, `velocity`, `airFlow`, `voc`, `soilMoisture`, `gasCubicMeters`, `waterCubicMeters`, `lastUpdate`, `deviceOnline`, `wakeUpInterval`, `rawLastReport`

Plug/Relay devices carry only: `switchState`, `watts`, `kwh`, `voltage`, `current`, `lastUpdate`, `deviceOnline`, `rawLastReport` (no battery or wake-up states — mains-powered)

---

## Z-Wave command classes handled

| Hex | Class | What it decodes |
|---|---|---|
| `0x31` | SENSOR_MULTILEVEL | Temperature, humidity, luminance, CO2, UV, pressure, noise, velocity, power (W), voltage (V), current (A), air flow, VOC, soil moisture |
| `0x30` | SENSOR_BINARY | Motion, water, smoke, CO, tamper, door/window |
| `0x71` | NOTIFICATION v4+ | Motion, tamper, intrusion, glass break, door/window, water, smoke, CO, lock/unlock ops (manual/RF/keypad/auto) |
| `0x62` | DOOR_LOCK | Lock mode, bolt state, latch state (v2+), last user |
| `0x5B` | CENTRAL_SCENE | Scene number, key action (pressed/released/held/repeated), sequence number |
| `0x25` | SWITCH_BINARY | On/off relay — Report and Set (association groups) |
| `0x26` | SWITCH_MULTILEVEL | Dimmers (0–99%) |
| `0x32` | METER | Power (W), energy (kWh/kVAh), voltage (V, Scale2), current (A, Scale2), gas (m3/ft3/ccf), water (m3/ft3/gallons) |
| `0x80` | BATTERY | Battery level %; 0xFF low warning |
| `0x20` | BASIC | Legacy on/off — Report and Set (many relays send Basic Set to association groups on input change) |
| `0x66` | BARRIER_OPERATOR | Garage doors and gates — open/closed/opening/closing/stopped plus position % |
| `0x60` | MULTI_CHANNEL | Endpoint encapsulation — unwrapped transparently, matches the originating endpoint |
| `0x6C` | SUPERVISION | Supervision encapsulation (S2-era devices) — unwrapped transparently |
| `0x56` | CRC-16 | CRC-16 encapsulation — unwrapped transparently |
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
2. Set Type to **Universal Z-Wave Sensor**
3. Set Model to the reading you want to capture — with these eleven models the model *is* the sensor type, so there is no separate dropdown to set:

   | Model | Captures |
   |---|---|
   | Motion Sensor | Motion and tamper |
   | Contact Sensor | Door and window contacts |
   | Temperature Sensor | Temperature |
   | Humidity Sensor | Relative humidity |
   | Luminance Sensor | Light level in lux |
   | Energy Monitor | Power, energy, voltage and current |
   | Battery Sensor | Battery percentage and a low-battery flag |
   | Lock | Lock mode, bolt and latch state, last user |
   | Scene Controller | Scene number and key action |
   | Plug / Relay | On and off control, plus energy monitoring |
   | Generic Sensor | Everything else the plugin decodes |

4. Click **Edit Device Settings**
5. Select the **Native Indigo Z-Wave Device** from the dropdown — the node ID is read automatically
6. *(Optional)* Enter an **Endpoint ID** for multi-channel devices

For a multi-sensor (e.g. door sensor that also sends temperature and humidity), create one plugin device per reading and select the same native device for each.

> **A twelfth model, Universal Z-Wave Sensor (Legacy), also appears in the list.** It is the original all-in-one type, where you pick the reading from a separate **Sensor Type** dropdown after choosing the native device. It stays in place so existing devices keep working — for anything new, pick one of the eleven models above.

> **Naming tip:** Name plugin devices to reflect what they add, e.g. `Bathroom Door (Temp)` or `Hall PIR (Humidity)`. When Indigo adds native support for those values, delete the plugin devices and update any triggers or action groups — a one-time job.

---

## When Indigo creates one generic device instead of several

The most common reason to reach for this plugin: you include a multi-sensor, and Indigo creates
a single device rather than the several you expected. The syncing lines in the event log show a
generic class such as `Routing Slave : Notification Sensor` or `Routing Slave : Binary Sensor`.

This usually means the manufacturer has changed the product ID, so Indigo doesn't yet have that
combination in its device database and falls back to the generic class it was told about. The
hardware is almost always fine.

### Step 1 — read the command classes to see what the device can actually report

The `retrieved command classes` line in the log is the useful part. A real example, from a Neo
Coolcam NAS-PD07Z that Indigo classed as a plain notification sensor:

```
Z-Wave Syncing - retrieved command classes: 20v1 5Ev1 98v1 9Fv1 6Cv1 55v1 86v1 73v1 85v1
                                            8Ev1 59v1 72v1 5Av1 87v1 71v1 30v1 31v11 70v1 7Av1
```

The classes worth looking for:

| Class | What its presence tells you |
|---|---|
| `31` SENSOR_MULTILEVEL | Temperature, humidity, luminance, CO2, UV, pressure and similar analogue readings |
| `71` NOTIFICATION | Motion, tamper, contact, water, smoke, CO — the modern reporting class |
| `30` SENSOR_BINARY | Motion, tamper, contact, water, smoke, CO — the older binary class |
| `32` METER | Power, energy, voltage, current, gas, water |
| `80` BATTERY | Battery percentage is reported, so a Battery device is worth creating |
| `84` WAKE_UP | Battery-powered and sleepy — reports only on wake-up or state change |
| `70` CONFIGURATION | Reporting intervals and thresholds can be changed (see step 3) |

In the example above, `31v11` confirms the temperature, humidity and luminance sensors are
present and `71`/`30` confirm the motion side — even though Indigo only surfaced one device.

Read the list as a description of **this inclusion**, not of the model. Neither `80` nor `84`
appears above, so a Battery companion device would have nothing to populate it — but that
particular sensor can run from either a CR2 cell or USB, and plenty of dual-powered Z-Wave
devices advertise the battery and wake-up classes only when they boot on the cell. If a reading
you expected is missing from the list, it is worth re-checking on the power source you actually
intend to use before concluding the device cannot report it.

Cross-reference anything you find against the [Z-Wave command classes handled](#z-wave-command-classes-handled)
table above to confirm this plugin decodes it.

### Step 2 — create one companion device per reading

Following the example: create a Temperature device, a Humidity device and a Luminance device,
and select the **same** native Indigo device for all three. They sit alongside the device Indigo
made, and each one carries a single reading.

### Step 3 — if nothing arrives, it is a reporting problem, not a decoding problem

The plugin can only decode what the sensor actually sends. If the lifeline association or the
reporting parameters were never set up at inclusion, the device may not be sending those reports
at all, and there is nothing to parse.

Turn on **Enable debug logging** in the plugin preferences and watch for `CC=0x31` lines while
the reading changes. If reports are arriving but the states are not updating, that is a plugin
issue worth raising. If nothing arrives at all, use the device's manual to find the reporting
interval and threshold parameters and set them via command class `70`.

### Step 4 — ask for native support

Companion devices are a stopgap. **Plugins → Universal Z-Wave Sensor → Generate Indigo Support
Report** dumps the manufacturer ID, product type and ID, supported command classes, properties
and states into the event log in one block, formatted for emailing to `support@indigodomo.com`
or pasting into the Indigo forum. Once Indigo supports the device natively, switch the devices
over to native — repoint anything that used a companion device, then delete it.

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

## Generate Indigo Support Report

**Plugins → Universal Z-Wave Sensor → Generate Indigo Support Report...**

Select a plugin device and click **Generate Report**. A formatted block is written to the Indigo log containing everything Matt and Jay (Indigo's authors) need to add native support for the device:

| Section | What it contains |
|---|---|
| Plugin Device | Name, type, node ID, endpoint, last update, raw last report bytes |
| Plugin Device States | All current state values |
| Native Z-Wave Device | Name, model, sub-model, description, protocol, Indigo ID |
| Native Device Z-Wave Properties | `ownerProps` — manufacturer ID, product type ID, product ID, supported command classes with versions |
| Native Device States | All states Indigo currently tracks for the native device |
| Native Device Global Props | All plugin-stored properties across every plugin |

Copy the entire block from the Indigo log and paste it into a post on the [Indigo forum](https://forums.indigodomo.com/viewforum.php?f=18).

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

The endpoint filter matches the **originating** endpoint of an incoming report (the device side, not the controller side), so a relay with a wired sensor input on endpoint 2 — the Zooz ZEN5x family, for example — can have its input split out into its own plugin device by setting Endpoint ID to 2.

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

## Logging

Every log line carries a millisecond timestamp `[HH:MM:SS.mmm]`, so you can
line events up precisely against the other CliveS plugins — Device Activity
Monitor uses the same format.

To turn the prefix off, or back on, at any time:

**Plugins → Universal Z-Wave Sensor → Toggle Timestamps in Log (on/off)**

The plugin stores the setting in `pluginPrefs` (`timestampEnabled`) and it
survives a restart. It defaults to ON.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 5.13 | 21-Jul-2026 | Housekeeping. Shared-utility refresh: calling the log timestamp filter twice no longer double-stamps every line, and the module imports cleanly outside Indigo. |
| 5.12 | 17-Jul-2026 | Deep-review improvements — new **Run Parser Self-Test** menu item (replays documented sample reports through the parsers and reports pass/fail, no hardware needed), new **Show Status** menu item (one-glance table of every monitored device), configurable low-battery warning threshold, 7-day and 14-day stale-threshold options, and an Energy/Plug status line that shows power instead of flapping between watts, volts, amps and kWh |
| 5.11 | 17-Jul-2026 | Deep-review test buildout — 35 new tests covering door-lock decoding, plug on/off/toggle control, the node map lifecycle, thermostat setpoints, scene controllers, lock-via-notification, the remaining notification types, and multi-layer encapsulation (suite now 182 tests) |
| 5.10 | 17-Jul-2026 | Deep-review hardening — stale detection survives a bad tick instead of stopping for good, a parser error on one sensor no longer drops reports for others sharing the same node, a stray report can no longer error on a mains plug, lock-user decoding fixed, and the verbose startup banner moved to the Show Plugin Info menu |
| 5.9 | 12-Jun-2026 | Supervision (CC 0x6C) and CRC-16 (CC 0x56) encapsulation now unwrapped transparently — S2-era devices wrap their reports in Supervision and these were previously dropped as unhandled. Endpoint filter now matches the originating endpoint of a report (was the controller-side endpoint, which silently dropped reports from relay sensor inputs such as the Zooz ZEN51/ZEN52/ZEN58 family). BASIC_SET and SWITCH_BINARY_SET handled — devices that report input changes to association groups via Set commands now update states. BARRIER_OPERATOR (CC 0x66) reports decoded — garage doors and gates (GoControl GD00Z and similar) surface open/closed/opening/closing/stopped and position %. Test suite repaired and extended to 127 tests |
| 5.8 | 25-May-2026 | Device communication now restarts only when the source device, the endpoint or the sensor type changes — the three settings that decide which native device a companion listens to, and the only ones that need the node map rebuilt. Other property writes no longer cause a needless restart |
| 5.7 | 23-May-2026 | Millisecond timestamp `[HH:MM:SS.mmm]` prefix on every `self.logger` line via `plugin_utils.install_timestamp_filter()`; new "Toggle Timestamps in Log" menu item |
| 5.6 | 10-May-2026 | Broader Z-Wave coverage. New handlers for HAIL (0x82), DEVICE_RESET_LOCALLY (0x5A), SCENE_ACTIVATION (0x2B), the three thermostat classes — mode (0x40), operating state (0x42) and setpoint (0x43) — and VERSION_REPORT (0x86). SENSOR_MULTILEVEL gained power, atmospheric pressure, target temperature and PM2.5. Eight further notification types decoded: heat, system, appliance, home health, siren, water valve, weather and gas. Generic and Legacy devices gained the matching states, and an unhandled event now logs a readable type name rather than a bare number |
| 5.5 | 04-May-2026 | Fix displayStatus state-not-defined error on Plug/Relay devices — all displayStatus writes now route through _safe_update and silently skip device types that do not define that state |
| 5.4 | 04-May-2026 | Generate Indigo Support Report menu item — dumps manufacturer ID, product type/ID, supported command classes, owner props, and all device states to the Indigo log, formatted for pasting into the Indigo forum; Show Plugin Info menu item added |
| 5.3 | 04-May-2026 | Removed battery/batteryLow/wakeUpInterval states from Plug/Relay device type (mains-powered, irrelevant) |
| 5.2 | 04-May-2026 | Plug/Relay device type (zwaveSensorPlug) — on/off control via actionControlDevice, energy monitoring (W/kWh/V/A), state sync at startup from native device; fix batteryLevel→battery (batteryLevel is a reserved Indigo native property — custom state silently dropped; use battery/Integer instead); Z-Wave protocol filter on native device picker; deviceStartComm re-entry guard (_devices_starting set) fixes maximum recursion depth error when stateListOrDisplayStateIdChanged() re-triggers startup |
| 5.1 | 04-May-2026 | Per-type state lists in Devices.xml — states now declared per device type rather than shared; battery state forced visible via _ensure_states_visible() on startup |
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

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.

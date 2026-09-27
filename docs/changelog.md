---
title: Version history
nav_order: 10
---

# Version history

The newest version is at the top.

## 5.14 — 7 September 2026

The plugin's settings window was wider than the screen allowed, so the help text beside each setting was cut off part-way. The help now sits in its own lines, which wrap to fit. No setting or behaviour changed.

## 5.13 — 21 July 2026

Behind-the-scenes tidying of the code shared with my other plugins. Log lines can no longer come out with the time printed twice.

## 5.12 — 17 July 2026

- New **Run Parser Self-Test** menu item, which checks the plugin reads fourteen sample messages correctly, without any hardware.
- New **Show Status** menu item, which writes a line for every device to the Event Log.
- New **Low-battery warning at** setting, where it used to be fixed at 20%.
- **Stale threshold** can be set to 7 or 14 days, for sensors that report rarely.
- An Energy Monitor or Plug / Relay shows its power in the device list, rather than jumping between power, energy, voltage and current as each arrived.

## 5.11 — 17 July 2026

More checks in the plugin's own test suite, covering locks, plugs, thermostats, scene buttons and wrapped messages. Nothing changed for users.

## 5.10 — 17 July 2026

- The check for quiet sensors carries on after an error, rather than stopping until the plugin is restarted.
- A problem reading a message for one device no longer stops other devices on the same sensor getting it.
- A stray battery message can no longer cause an error on a Plug / Relay.
- A lock message that carries no user code is no longer mistaken for one that does.
- Turning off **Enable stale device detection** sets any device left marked offline back to online.
- The long block of details the plugin wrote to the log at start-up has moved to **Show Plugin Info**.

## 5.9 — 12 June 2026

- Newer secure devices, and some older ones, wrap their messages in an extra layer. The plugin now unwraps them, where before it dropped them.
- **Endpoint ID** now matches the part of the sensor a message came from. Before, messages from a sensor input on a relay, such as the Zooz ZEN51, ZEN52 and ZEN58, were dropped.
- Relays that send their switch changes as commands, rather than as reports, now update the device.
- Garage door and gate openers show open, closed, opening, closing, stopped and how far open.

## 5.8 — 25 May 2026

A device only restarts when you change its native device, its Endpoint ID or its Sensor Type, not whenever anything about it changes.

## 5.7 — 23 May 2026

Every log line starts with the time to the thousandth of a second, with a menu item to turn that off.

## 5.6 — 10 May 2026

- Reads more kinds of message: thermostat mode, operating state and setpoints, older scene buttons, firmware version, a device saying it has news, and a device reporting it has been reset.
- New readings for power, atmospheric pressure, a thermostat's target temperature and PM2.5.
- Understands more alarms: heat, system faults, appliances, health, sirens, water valves, weather and gas.
- The Generic Sensor gained the matching readings.

## 5.5 — 4 May 2026

Fixed an error on Plug / Relay devices, which have no Status reading, when the plugin tried to set one.

## 5.4 — 4 May 2026

New **Generate Indigo Support Report** menu item, and **Show Plugin Info**.

## 5.3 — 4 May 2026

Plug / Relay devices no longer carry battery readings, as they run from the mains.

## 5.2 — 4 May 2026

- New **Plug / Relay** model, which you can switch on and off, with power and energy readings. It starts with the same on or off as Indigo's own device.
- The battery level shows properly in Indigo's list of device states.
- The **Native Indigo Z-Wave Device** list only shows Z-Wave devices.
- Fixed a fault that could make a device restart over and over when it started.

## 5.1 — 4 May 2026

Each model now carries only the readings that suit it, rather than every model carrying every reading.

## 5.0 — 3 May 2026

- New **Lock** model, with locked or unlocked, bolt, latch and the user code number.
- New **Scene Controller** model, with the button and how it was pressed.
- New **Battery Sensor** model, and a **Battery Low** reading on every device.
- Locks locked or unlocked by hand, keypad, remote or automatically, intrusion and glass breaking are all recognised.
- Gas and water meters, and air speed, air flow, VOC and soil moisture readings.

## 4.0 — 22 March 2026

Energy monitors show voltage and current as well as power and energy.

## 3.9 — 22 March 2026

The plugin's version shows properly in Indigo, and details of the plugin are written to the log at start-up.

## 3.8 — 22 March 2026

Sensors that report motion in both the older and the newer way no longer write it to the log twice.

## 3.7 — 22 March 2026

A reading is only written to the Event Log against the device it belongs to, so the log is much quieter.

## 3.6 — 22 March 2026

A device's device-list line is set correctly as soon as the plugin starts.

## 3.5 — 22 March 2026

Motion no longer overwrites the device-list line on a temperature or light device made from the same sensor.

## 3.4 — 22 March 2026

Fixed motion being shown as clear when some sensors reported it as seen, and recognised another way sensors report motion.

## 3.3 — 22 March 2026

Fixed messages arriving from Indigo not being read.

## 3.2 — 22 March 2026

You always choose the device Indigo made for the sensor, rather than typing in a node number.

## 3.1 — 22 March 2026

The plugin hears messages from sensors Indigo already has a device for, which is what lets it sit alongside Indigo's own device. It also copes with older sensors that send parts of their alarm messages in a different order.

## 3.0 — 21 March 2026

Sensors with several parts, warnings for sensors that go quiet, the choice of Celsius or Fahrenheit, and the wake-up interval of battery sensors. The Simulate window stays open after each message.

## 2.2 — 21 March 2026

New **Simulate Z-Wave Report** menu item.

## 2.1 — 21 March 2026

A warning when you made a device for a sensor Indigo already looks after. Version 3.1 removed it, when the plugin learnt to work alongside Indigo's own devices.

## 2.0 — 21 March 2026

The plugin reads the sensor's messages itself, rather than copying readings from Indigo's own devices.

## 1.5 — 21 March 2026

The first version published on GitHub.

## 1.0 — 20 March 2026

The first version.

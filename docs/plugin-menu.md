---
title: The plugin menu
nav_order: 8
---

# The plugin menu

These are under **Plugins → Universal Z-Wave Sensor**.

| Menu item | What it does |
|---|---|
| **Simulate Z-Wave Report...** | Feeds a message you type in to one of your plugin devices, as if its sensor had sent it. Explained below. |
| **Generate Indigo Support Report...** | Writes everything Indigo's authors need to support a sensor properly to the Event Log, ready to post on the Indigo forum. Explained below. |
| **Show Status** | Writes a table to the Event Log with one line per plugin device: its name, node number, model, whether it is online, offline or stale, and when its sensor last reported. |
| **Run Parser Self-Test** | Runs fourteen sample messages — temperature, humidity, light, motion, a door, a leak, a lock, scene buttons, battery, a switch, a power meter, a garage door and a wrapped motion message — through the plugin's readers, and writes a pass or fail line for each to the Event Log, with a total at the end. It uses a pretend device, so none of your devices change and nothing is sent to your Z-Wave network. Every line should say `PASS`. |
| **Toggle Timestamps in Log (on/off)** | Every line the plugin writes to the log starts with the time to the thousandth of a second, which helps when lining events up. This turns that on or off. It stays as you leave it. |
| **Show Plugin Info** | Writes the plugin's version and details of your Mac and Indigo to the log, which is useful to include if you ask for help on the Indigo forum. |

## Simulate Z-Wave Report

Choose a device in **Plugin Device**, type a message into **Hex Bytes**, and click **Send**. The plugin reads the message exactly as if the sensor had sent it, and the device's readings change. The window stays open so you can send another.

It is a real change to a real device, so any trigger watching that device will run. Pick a device nothing important depends on, or expect the trigger.

A message is a row of pairs of characters separated by spaces, the same way the plugin writes them in the Event Log with debug logging on. These work on any device of the matching model:

| Message | What it simulates |
|---|---|
| `31 05 01 22 00 D7` | Temperature 21.5 degC |
| `31 05 05 01 41` | Humidity 65% |
| `31 05 03 0A 01 C2` | Light level 450 lux |
| `71 05 00 00 00 FF 07 07 00` | Motion seen |
| `71 05 00 00 00 FF 07 00 00` | Motion clear |
| `71 05 00 00 00 FF 06 16 00` | Door opened |
| `71 05 00 00 00 FF 06 17 00` | Door closed |
| `62 03 FF` | Lock locked |
| `62 03 00` | Lock unlocked |
| `5B 03 01 00 01` | Scene 1, pressed |
| `5B 03 02 03 02` | Scene 2, pressed twice |
| `80 03 55` | Battery 85% |
| `80 03 FF` | The sensor's own low-battery warning |
| `84 06 00 01 2C 6F` | Wakes every 300 seconds |

The easiest way to test a real problem is to copy a line from the Event Log with debug logging on, and paste its message in here.

## Generate Indigo Support Report

Choose one of your plugin devices in **Plugin Device** and click **Generate Report**. The Event Log gets one block with:

- **The plugin device** — its name, model, node number, Endpoint ID, when it last heard from the sensor, the last message it could not read, and all its readings.
- **The native device Indigo made** — its name, model, and the properties Indigo stores for it, which include the maker's number, the product numbers and the families of messages the sensor can send.
- **The native device's readings**, and anything other plugins store against it.

Copy the whole block from the Event Log and post it on the [Indigo forum](https://forums.indigodomo.com) when you ask for the sensor to be supported. The window stays open, so you can make a report for another device.

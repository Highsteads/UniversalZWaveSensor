---
title: One device instead of several
nav_order: 5
---

# When Indigo makes one device instead of several

This is the most common reason to reach for the plugin. You add a multi-sensor to Indigo and get a single plain device rather than the several you expected. The lines Indigo writes to the Event Log while it adds the device describe it in general terms, such as `Routing Slave : Notification Sensor` or `Routing Slave : Binary Sensor`.

Usually the maker has changed the model's product number, so Indigo does not have that exact model in its list yet and falls back on a general description. The sensor itself is almost always fine.

## Step 1 — see what the sensor says it can send

While Indigo adds a device, the Event Log has a line that starts `retrieved command classes`. It lists every family of messages the device says it can send — Z-Wave calls these families **command classes**. Here is a real one, from a Neo Coolcam NAS-PD07Z that Indigo made into a plain notification sensor:

```
Z-Wave Syncing - retrieved command classes: 20v1 5Ev1 98v1 9Fv1 6Cv1 55v1 86v1 73v1 85v1
                                            8Ev1 59v1 72v1 5Av1 87v1 71v1 30v1 31v11 70v1 7Av1
```

Each entry is the family's number, then `v` and its version. Ignore the version and look for these numbers:

| Number | If it is there |
|---|---|
| `31` | The sensor sends readings such as temperature, humidity, light level, CO2, UV or air pressure |
| `71` | The sensor sends events such as motion, tamper, door contact, water, smoke or carbon monoxide |
| `30` | The sensor sends the same kind of on and off events in the older way |
| `32` | The sensor measures power, energy, voltage, current, gas or water |
| `80` | The sensor reports its battery level, so a Battery Sensor device is worth making |
| `84` | The sensor sleeps between reports to save its battery, and only sends when something changes or when it wakes |
| `70` | The sensor has settings of its own that can be changed, such as how often it reports (see step 3) |

In the example, `31` shows the temperature, humidity and light sensors are there, and `71` and `30` show the motion side is there, even though Indigo only made one device.

Read the list as a description of this one time the sensor was added, not of the model. Neither `80` nor `84` appears above, so a Battery Sensor device would have nothing to show — but that sensor can run from either a CR2 battery or USB power, and plenty of sensors that can use both only list the battery families when they start up on the battery. If a reading you expected is missing, check the list again with the sensor on the power source you mean to use before deciding it cannot send it.

The [How it works](how-it-works.md#what-the-plugin-can-read) page lists every family the plugin can read.

## Step 2 — make one device per reading

Following the example, make a **Temperature Sensor**, a **Humidity Sensor** and a **Luminance Sensor**, and choose the **same** native device in each. They sit alongside the device Indigo made, and each shows one reading. [Getting started](getting-started.md) goes through it step by step.

## Step 3 — if nothing arrives, the sensor is not sending it

The plugin can only read what the sensor actually sends. If the sensor was never set up to send a reading when it was added, it may not be sending it at all, and there is nothing for the plugin to read.

To check, tick **Enable debug logging** in **Plugins → Universal Z-Wave Sensor → Configure**, make the reading change, and watch the Event Log. Every message from the sensor appears as a line with `CC=0x` and the family number, such as `CC=0x31` for a reading.

- **If the messages arrive but the device does not change**, the plugin is not reading them properly. Please raise it on [GitHub](https://github.com/Highsteads/UniversalZWaveSensor/issues) or the Indigo forum with those log lines.
- **If nothing arrives at all**, the sensor needs telling to send it. Most sensors keep numbered settings inside themselves, which Z-Wave calls **parameters** — how often to report, and how big a change is worth reporting. The sensor's manual lists them, and they are set from Indigo's own Z-Wave tools, not from this plugin.

Remember to untick **Enable debug logging** afterwards, as it adds a line to the log for every message.

## Step 4 — ask for proper support

The plugin's devices are a stopgap. Choose **Plugins → Universal Z-Wave Sensor → Generate Indigo Support Report**, pick one of the plugin's devices for the sensor, and click **Generate Report**. It writes everything Indigo's authors need to support the model — the maker's and product numbers, the families of messages it sends, and all its settings and readings — to the Event Log in one block. Copy the block and post it on the [Indigo forum](https://forums.indigodomo.com).

Once Indigo supports the sensor properly, switch over: point any triggers, control pages and action groups at Indigo's own device, then delete the plugin's devices for it.

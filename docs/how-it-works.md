---
title: How it works
nav_order: 4
---

# How it works

You do not need to know any of this to use the plugin. It is here for anyone who likes to know what is going on, and it helps when a reading does not arrive.

## Listening alongside Indigo

When the plugin starts, it asks Indigo to pass it a copy of every message that arrives from your Z-Wave network, including messages from devices Indigo already looks after. It keeps the ones that come from the node numbers of your plugin devices and ignores the rest.

Indigo still gets every message too, so the device Indigo made carries on exactly as before. The plugin only listens. It sends nothing to your Z-Wave network itself, apart from passing on your on and off commands for a **Plug / Relay** device, which it does through Indigo's own device.

When the plugin starts, the Event Log has a line saying how many node numbers it is listening to, and one for each device.

## What the plugin can read

Z-Wave sorts the messages a device sends into numbered families, one family for each kind of thing — sensor readings, battery level, door locks and so on. Z-Wave calls each family a **command class**. Indigo's log writes them as two characters, such as `31` or `5B`, and the plugin reads these:

| Family | What it carries |
|---|---|
| `31` | Readings such as temperature, humidity, light level, power, voltage, current, CO2, UV, air pressure, noise, air speed, air flow, VOC, soil moisture, PM2.5 and a thermostat's target temperature |
| `30` | Older on and off sensors — motion, door contact, water, smoke, carbon monoxide, tamper |
| `71` | Alarms and events — motion, tamper, intrusion, glass breaking, doors opening and closing, water, smoke, carbon monoxide, heat, gas, sirens, water valves, power and battery warnings, and locks being locked or unlocked by hand, keypad or remote |
| `62` | Door locks — locked or unlocked, bolt and latch |
| `5B` | Scene buttons — which button, and how it was pressed |
| `2B` | Older scene buttons that send a plain scene number |
| `32` | Meters — electricity (power, energy, voltage, current), gas and water |
| `25`, `26`, `20` | Switches, dimmers and plain on and off messages, including those a relay sends when a switch wired to it changes |
| `66` | Garage door and gate openers — open, closed, opening, closing, stopped and how far open |
| `40`, `42`, `43` | Thermostats — mode, whether heating or cooling now, and setpoints |
| `80` | Battery level |
| `84` | Wake-up messages from battery sensors, and how often they wake |
| `86` | The device's firmware version |
| `82` | A device saying it has news, which counts as a sign of life |
| `5A` | A device saying it has been reset to factory settings |

Some devices wrap their messages in extra layers before sending them — newer secure devices, devices with several parts, and some that add a check number to each message. The plugin unwraps families `6C`, `60` and `56` to get at the message inside. Indigo removes the Z-Wave security before the plugin sees anything, so secure devices work the same as others.

A message from any other family is not understood. With **Log unknown command classes** ticked, it is written to the Event Log and kept in the device's **Last Raw Report**.

## One sensor, several devices

Every plugin device you point at the same native device gets a copy of every message from that sensor. Each one keeps only the readings it has room for — a Temperature Sensor keeps temperature and ignores humidity — so you can make one device per reading and each shows only its own.

Temperature, humidity, light, motion and door readings are only written to the Event Log against the device they belong to, so a humidity reading does not also appear against the sensor's temperature device.

## Sensors with several parts

Some devices are really several devices under one node number — a multi-sensor with separate parts for motion, temperature and light, or a relay with a sensor input wired to it. Z-Wave calls each part an **endpoint** and gives it its own number, 1, 2, 3 and so on.

Leave **Endpoint ID** blank, or set it to 0, and the device takes messages from every part. Set it to a number and the device only takes messages from that part. For example, for a sensor with motion on part 1, temperature on part 2 and light on part 3:

| Plugin device | Model | Endpoint ID |
|---|---|---|
| Hall Motion | Motion Sensor | 1 |
| Hall Temperature | Temperature Sensor | 2 |
| Hall Light | Luminance Sensor | 3 |

A relay with a sensor input, such as those in the Zooz ZEN5x range, can have the input split out into its own device the same way.

A message the sensor sends without any part number is still taken by every device on that node, whatever its Endpoint ID. To find which part number a reading comes from, tick **Enable debug logging**, make the sensor send the reading, and look in the Event Log for a line naming `src_ep` — the number after it is the part it came from.

## Temperatures

Sensors report in Celsius or Fahrenheit. The plugin converts every temperature and thermostat setpoint to the unit you chose in **Temperature unit** before storing it, so all your devices agree. A change to the unit applies to the next reading each sensor sends.

## Sensors that go quiet

Once a minute the plugin looks at when each device last heard from its sensor. If that is longer ago than the **Stale threshold**, the device's **Online** state is set to offline and the Event Log has one warning, such as `No report for 26.3h (threshold 24h) — may be offline or out of range`. The warning is not repeated. The moment the sensor sends anything, the device is set back to online and the log says it is back.

A device that has never heard from its sensor is left alone, because there is nothing to measure its silence from.

A battery sensor may only report every few hours, or even less often, so give it a threshold well beyond its usual gap.

## What the plugin cannot do

- **It cannot ask a battery sensor for a reading.** The sensor sends when something changes or when it wakes on its own timetable. The plugin waits for it.
- **It cannot make a sensor send a reading it has not been set up to send.** If a sensor was never told to report something, there is nothing to read. [One device instead of several](one-device-instead-of-several.md) covers this.
- **It does not read maker-specific messages**, which each manufacturer defines for itself. They go in **Last Raw Report** like any other unknown message.

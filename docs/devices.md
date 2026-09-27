---
title: Your devices
nav_order: 3
---

# Your devices

Each device you make with this plugin carries one reading from one Z-Wave sensor, chosen by its **Model**. This page explains what each model shows. The names in the tables are the ones you see when you add a device state to a control page or pick one in a trigger.

## What every model shows

Every model except **Plug / Relay** carries these as well as its own readings.

| Shown as | What it means |
|---|---|
| **Status** | The short line shown in Indigo's device list, such as `21.5 degC`, `open` or `S1 pressed`. |
| **Active** | On or off. It follows the latest on or off message from the sensor — motion seen, a door opened, a lock locked — so on a Temperature Sensor made from a motion sensor, it follows the motion. |
| **Battery %** | The battery level the sensor last reported. If the sensor sends its own "battery low" warning instead of a number, this shows `LOW`. |
| **Battery Low** | On when the battery is at or below the level set in **Low-battery warning at** (20% to start with), when the sensor sends its own low-battery warning, or when it asks for its battery to be replaced. |
| **Last Updated** | The date and time of the last message from the sensor, such as `2026-09-27 09:15:04`. |
| **Online** | Online from the moment the plugin starts the device, and again every time the sensor sends anything. Set to offline when the sensor has sent nothing for longer than the **Stale threshold**. Shows `reset` if the sensor reports it has been reset to factory settings. |
| **Wake-up Interval** | How often a battery sensor wakes up on its own, such as `5m 0s`. It only fills in when the sensor reports it. |
| **Last Raw Report** | The last message the plugin could not read, written as the numbers the sensor sent. It is there to paste into a request for help. |

## Motion Sensor

| Shown as | What it means |
|---|---|
| **Motion** | On when motion is seen, off when the sensor says all is clear. |
| **Tamper** | On when the sensor says its cover has been opened or it has been moved. |

The device list shows `detected`, `clear`, `tamper`, `intrusion` or `glass break`, whichever the sensor last reported.

## Contact Sensor

| Shown as | What it means |
|---|---|
| **Door/Window** | On when open, off when closed. |
| **Tamper** | On when the sensor says its cover has been opened or it has been moved. |

The device list shows `open` or `closed`. A garage door or gate opener also reports here, and shows `opening`, `closing`, `stopped`, `open` or how far open it is, such as `open 50%`.

## Temperature Sensor

**Temperature** shows the reading in the unit you chose in the plugin's settings, converted if the sensor sends the other one. The device list shows it too, such as `21.5 degC`.

## Humidity Sensor

**Humidity %** shows the relative humidity, such as `65 %`.

## Luminance Sensor

**Luminance (lux)** shows the light level, such as `450 lux`. Some sensors report light as a percentage rather than in lux, and then the device list shows a percentage.

## Energy Monitor

| Shown as | What it means |
|---|---|
| **Power (W)** | The power being used right now, in watts. |
| **Energy (kWh)** | The total energy used, in kilowatt hours, as the device counts it. |
| **Voltage (V)** | The mains voltage. |
| **Current (A)** | The current being drawn, in amps. |

The device list shows the power. The other readings arrive at different moments, so showing only the power stops the line jumping between four different numbers.

## Battery Sensor

**Battery %** and **Battery Low**, as above. The device list shows the percentage, or `LOW`, and **Active** is on while the battery is fine and off when it is low, so a trigger on the device turning off tells you the battery needs changing.

## Lock

| Shown as | What it means |
|---|---|
| **Locked** | On when locked, off when unlocked. |
| **Lock Mode** | The lock's own number for its mode. 255 means locked and 0 means unlocked. |
| **Bolt Locked** | On when the bolt is thrown, if the lock reports it. |
| **Latch Closed** | On when the latch is closed, if the lock reports it. |
| **Last User** | The number of the user code used to lock or unlock it from the keypad or remotely, when the lock sends one. |

The device list shows `locked`, `unlocked` or `jammed`. A jammed lock also puts a warning in the Event Log.

## Scene Controller

For wall switches, remotes and buttons that send a scene number when you press them.

| Shown as | What it means |
|---|---|
| **Last Scene** | The number of the button or scene used. Some controllers count from 0 and some from 1 — press each button once and note what it sends. |
| **Last Action** | How it was pressed: `pressed`, `released`, `held`, `double`, `triple`, `quad` or `quint`. Older controllers that send a plain scene number show `activated`. |
| **Scene Time** | The date and time of the press. |

The device list shows both together, such as `S1 pressed`. **Active** is on for every press and off when a held button is released.

## Plug / Relay

For a plug or relay that Indigo sees but does not show fully. You switch it with Indigo's usual **Turn On**, **Turn Off** and **Toggle**, and the plugin passes the command to the device Indigo made for it. See [Triggers and switching](triggers-and-switching.md).

| Shown as | What it means |
|---|---|
| **On / Off** | Whether the plug is on. It is copied from Indigo's own device when the plugin starts, and follows the plug's messages after that. |
| **Switch** | The same on or off, as the plug last reported it. |
| **Power (W)**, **Energy (kWh)**, **Voltage (V)**, **Current (A)** | As for the Energy Monitor, if the plug measures them. |
| **Last Updated**, **Online**, **Last Raw Report** | As in the first table. |

A plug runs from the mains, so this model has no battery readings.

## Generic Sensor

For anything the other models do not cover. The device list shows the latest alarm, switch, meter or thermostat message, and the device carries these:

| Group | Shown as |
|---|---|
| Switches and dimmers | **Switch**, **Dim Level %** |
| Air and weather | **CO2 (ppm)**, **UV Index**, **Pressure (kPa)**, **Atmospheric Pressure**, **Noise (dB)**, **Velocity (m/s)**, **Air Flow (m3/h)**, **VOC (ppm)**, **PM2.5 (ug/m3)**, **Soil Moisture %** |
| Gas and water meters | **Gas (m3)**, **Water (m3)** |
| Alarms | **Water Leak**, **Smoke**, **CO Alarm**, **Heat Alarm**, **Gas Leak**, **Siren Active**, **Valve Open** |
| Thermostats | **Thermostat Mode**, **Operating State**, **Setpoint**, **Setpoint Type**, **Target Temperature** |
| About the device | **Firmware Version** |

It does not carry temperature, humidity, light level, motion, door contact or power. Use the matching model for those.

## Universal Z-Wave Sensor (Legacy)

The single model versions before 5.1 used, where a separate **Sensor Type** setting chose the reading. It carries every reading from every model above, and stays so that older devices keep working. Use one of the models above for anything new.

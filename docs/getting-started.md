---
title: Getting started
nav_order: 2
---

# Getting started

This takes a few minutes per sensor.

## What you need

- Indigo 2022.1 or later, with the Z-Wave stick or interface Indigo already uses for your Z-Wave devices.
- The sensor already added to your Z-Wave network through Indigo in the usual way, so Indigo has made a device for it. The plugin reads everything it needs from that device, and does not add anything to your Z-Wave network itself.

A word you will meet on the way: every Z-Wave device on your network has a **node number**, the number Indigo gave it when you added it. It shows as the device's **Address** in Indigo's device list. The plugin uses it to know which messages come from which sensor, and reads it for you.

## 1. Install the plugin

1. Go to the [Releases page](https://github.com/Highsteads/UniversalZWaveSensor/releases/latest) and download `UniversalZWaveSensor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `UniversalZWaveSensor.indigoPlugin`
3. Double-click `UniversalZWaveSensor.indigoPlugin` — Indigo will install it automatically

Indigo asks whether to enable the plugin. Say yes.

## 2. Check the settings

Open **Plugins → Universal Z-Wave Sensor → Configure**. The settings work as they are for most people, so the one to look at is **Temperature unit**, which is Celsius to start with. Click **Save**. Every setting is explained on the [Settings](settings.md) page.

## 3. Add a device for one reading

1. In Indigo, choose **New Device**.
2. Set **Type** to **Universal Z-Wave Sensor**.
3. Set **Model** to the reading you want:

   | Model | What it shows |
   |---|---|
   | **Motion Sensor** | Motion, and whether the sensor's cover has been opened |
   | **Contact Sensor** | A door or window open or closed |
   | **Temperature Sensor** | Temperature |
   | **Humidity Sensor** | Humidity |
   | **Luminance Sensor** | Light level |
   | **Energy Monitor** | Power, energy used, voltage and current |
   | **Battery Sensor** | Battery level, and whether it is low |
   | **Lock** | Locked or unlocked, the bolt and latch, and which user code was used |
   | **Scene Controller** | Which button was pressed, and how |
   | **Plug / Relay** | On and off, which you can switch, with power and energy use |
   | **Generic Sensor** | Most of the other readings the plugin understands |

   A twelfth model, **Universal Z-Wave Sensor (Legacy)**, is only there so devices made with versions before 5.1 keep working. Do not choose it for a new device.

4. In **Native Indigo Z-Wave Device**, choose the device Indigo made for the sensor. The list shows each of Indigo's Z-Wave devices with its node number beside the name.
5. Leave **Endpoint ID** blank unless the sensor needs it. The [How it works](how-it-works.md#sensors-with-several-parts) page explains when it does.
6. Click **Save**, and give the device a name that says what it adds, such as `Hall Sensor (Temperature)`.

For a sensor that measures several things, repeat this once for each reading you want, choosing the **same** native device each time. Each new device carries one reading.

## 4. Check it works

When you save, the Indigo Event Log shows a line saying the device is now listening on the sensor's node number.

Now make the sensor send something — walk past a motion sensor, open the door a contact sensor is fitted to, breathe on a humidity sensor. Within a moment the new device shows the reading in Indigo's device list, and for most readings the Event Log has a line with the new value.

A battery-powered sensor only sends a reading when something changes or when it wakes up on its own timetable, which can be hours apart. If nothing arrives, press the sensor's button to wake it, or give it time.

If a reading still never appears, the [When something goes wrong](troubleshooting.md) page goes through the usual causes, and [One device instead of several](one-device-instead-of-several.md) shows how to check which readings the sensor can send at all.

---
title: Home
nav_order: 1
---

# Universal Z-Wave Sensor for Indigo

When you add a Z-Wave sensor to [Indigo](https://www.indigodomo.com), Indigo makes a device for it from what it knows about that model. If Indigo does not know the model yet, or only knows part of it, you can end up with a device that shows motion but not the temperature, humidity or light level the sensor is also sending.

This plugin reads the messages the sensor sends and turns the missing readings into Indigo devices of their own. Each one sits alongside the device Indigo made, which carries on working exactly as before, and each works in triggers, control pages and action groups like any other Indigo device.

It is a stopgap for devices Indigo does not yet fully support. Once Indigo supports a device properly, you switch over to Indigo's own device and delete the plugin's.

## What it does for you

- **Shows the readings Indigo leaves out** — temperature, humidity, light level, power and energy use, door and window contacts, locks, scene buttons, battery level and more.
- **Makes one Indigo device per reading**, so a sensor that measures five things can have five devices, each showing one clear value in the device list.
- **Switches a plug or relay** from the plugin's own device, by passing the command to the device Indigo made for it.
- **Converts every temperature** to Celsius or Fahrenheit, whichever you choose, whatever the sensor sends.
- **Warns you when a sensor goes quiet** for longer than you allow, and says when it comes back.
- **Writes a support report** with everything Indigo's authors need to add proper support for the device, ready to post on the Indigo forum.
- **Lets you test without the hardware** by typing in a message as if the sensor had sent it.

## Where to go next

| If you want to... | Read |
|---|---|
| Install the plugin and add your first device | [Getting started](getting-started.md) |
| Know what each device shows in Indigo | [Your devices](devices.md) |
| Understand what the plugin is doing behind the scenes | [How it works](how-it-works.md) |
| Work out which readings a sensor can send when Indigo made only one device | [One device instead of several](one-device-instead-of-several.md) |
| Use the devices in triggers, or switch a plug | [Triggers and switching](triggers-and-switching.md) |
| Know what every setting does | [Settings](settings.md) |
| Know what each item in the Plugins menu does | [The plugin menu](plugin-menu.md) |
| Sort out a problem | [When something goes wrong](troubleshooting.md) |
| See what changed in each version | [Version history](changelog.md) |

## Download

The latest version is always on the [Releases page](https://github.com/Highsteads/UniversalZWaveSensor/releases/latest).

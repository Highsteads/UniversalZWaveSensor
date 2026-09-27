# Universal Z-Wave Sensor for Indigo

**Show the readings Indigo leaves out when it does not fully know a Z-Wave sensor, as Indigo devices of their own.**

**Version:** 5.14 | **Author:** CliveS & Claude | **Needs:** Indigo 2022.1 or later, with a Z-Wave interface

**[Read the full guide](https://highsteads.github.io/UniversalZWaveSensor/)** — setting up, what everything means, and what to do when something goes wrong.

---

## What it does

When you add a Z-Wave sensor to [Indigo](https://www.indigodomo.com), Indigo makes a device from what it knows about that model. If it does not know the model yet, you can end up with one plain device that shows motion but not the temperature, humidity or light level the sensor is also sending. This plugin reads the sensor's messages and gives each missing reading an Indigo device of its own, alongside the one Indigo made, which carries on as before.

- **Shows the readings Indigo leaves out** — temperature, humidity, light level, power and energy use, door and window contacts, locks, scene buttons, battery level, alarms, meters and thermostats.
- **Makes one Indigo device per reading**, each with a clear value in the device list, working in triggers, control pages and action groups like any other device.
- **Switches a plug or relay** by passing your command to the device Indigo made for it.
- **Converts every temperature** to Celsius or Fahrenheit, whichever you choose.
- **Warns you when a sensor goes quiet** for longer than you allow, and says when it comes back.
- **Writes a support report** with everything Indigo's authors need to support the sensor properly, ready to post on the Indigo forum.
- **Lets you test without the hardware** by typing in a message as if the sensor had sent it.

## What it works with

Any Z-Wave device you have already added to your network through Indigo, so that Indigo has made a device for it. The plugin reads its messages alongside Indigo, and adds nothing to your Z-Wave network itself. For each reading you choose a model:

| Model | What it shows |
|---|---|
| **Motion Sensor** | Motion, and tamper |
| **Contact Sensor** | Door or window open or closed, and garage doors and gates |
| **Temperature Sensor**, **Humidity Sensor**, **Luminance Sensor** | One reading each |
| **Energy Monitor** | Power, energy used, voltage and current |
| **Battery Sensor** | Battery level, and whether it is low |
| **Lock** | Locked or unlocked, bolt, latch, and the user code used |
| **Scene Controller** | Which button was pressed, and how |
| **Plug / Relay** | On and off, which you can switch, with power and energy use |
| **Generic Sensor** | Alarms, meters, air quality, thermostats and most other readings |

## Installing

1. Go to the [Releases page](https://github.com/Highsteads/UniversalZWaveSensor/releases/latest) and download `UniversalZWaveSensor.indigoPlugin.zip`
2. Unzip the downloaded file — you will get `UniversalZWaveSensor.indigoPlugin`
3. Double-click `UniversalZWaveSensor.indigoPlugin` — Indigo will install it automatically

## Setting it up

1. Open **Plugins → Universal Z-Wave Sensor → Configure**, choose Celsius or Fahrenheit in **Temperature unit**, and click **Save**.
2. Create a **New Device**, choose **Universal Z-Wave Sensor** and the model for the reading you want, and in **Native Indigo Z-Wave Device** choose the device Indigo made for the sensor.
3. Repeat for each reading you want from the same sensor, choosing the same native device each time.
4. Make the sensor send something — walk past it, open the door — and the new device shows the reading.

The [full guide](https://highsteads.github.io/UniversalZWaveSensor/) goes through each step, explains every setting, and shows how to work out which readings a sensor can send when Indigo made only one device.

## What's new

**v5.14** — The settings window was wider than the screen allowed, so the help text beside each setting was cut off. The help now wraps to fit. No setting or behaviour changed.

**v5.13** — Behind-the-scenes tidying of the code shared with my other plugins. Log lines can no longer come out with the time printed twice.

**v5.12** — New **Run Parser Self-Test** and **Show Status** menu items, a **Low-battery warning at** setting, 7 and 14 day choices for **Stale threshold**, and an Energy Monitor or Plug / Relay shows its power in the device list rather than jumping between readings.

Every version is listed in the [version history](https://highsteads.github.io/UniversalZWaveSensor/changelog.html).

## Authors & licence

Vibed into existence by **CliveS**, who knew what he wanted, argued until he got it, and tested it on a real house. Typed at inhuman speed by **Claude** (Anthropic), who mostly did as it was told.

© 2026 CliveS · [MIT licence](LICENSE) — copy it, fork it, bend it, break it, fix it, ship it. If it breaks, you get to keep both pieces.

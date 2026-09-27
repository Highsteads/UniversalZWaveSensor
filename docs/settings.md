---
title: Settings
nav_order: 7
---

# Settings

## The plugin's settings

Open these with **Plugins → Universal Z-Wave Sensor → Configure**. They apply to every device, and take effect as soon as you click **Save**.

| Setting | What it does |
|---|---|
| **Enable debug logging** | Writes every message from your sensors to the Event Log as it arrives, along with every reading the plugin stores. Useful when you first add a new sensor or are chasing a problem, but it adds a great many lines, so untick it afterwards. Off to start with. |
| **Log unknown command classes** | When a sensor sends a message the plugin does not understand, writes it to the Event Log and keeps it in the device's **Last Raw Report**, ready to pass on if you ask for help. On to start with. |
| **Temperature unit** | **Celsius (degC)** or **Fahrenheit (degF)**. Every temperature and thermostat setpoint is converted to this before it is stored, whatever the sensor sends. It applies from each sensor's next reading. Celsius to start with. |
| **Enable stale device detection** | Warns you when a sensor has sent nothing for longer than the **Stale threshold**, and sets its device's **Online** state to offline until it next reports. Unticking it sets any device marked offline back to online. On to start with. |
| **Stale threshold** | How long a sensor can stay quiet before it counts as offline: 4, 8, 12, 24, 48 or 72 hours, 7 days or 14 days. 24 hours to start with. Many battery sensors only report every few hours or less, so allow them plenty. |
| **Low-battery warning at** | The battery level, from 10% to 30%, at or below which a device's **Battery Low** turns on. 20% to start with. Raise it for earlier warning. |

The plugin keeps no passwords or addresses, so it needs nothing from a shared settings file.

## Each device's settings

Open these by double-clicking a plugin device in Indigo.

| Setting | What it does |
|---|---|
| **Native Indigo Z-Wave Device** | The device Indigo made for the sensor. The list shows each of Indigo's Z-Wave devices with its node number, and the plugin reads the node number from the one you choose. |
| **Endpoint ID** | Only for a device with several parts under one node number. Blank or 0 takes messages from every part, and a number from 1 to 255 takes them only from that part. [How it works](how-it-works.md#sensors-with-several-parts) explains it. |
| **Sensor Type** | Only on the **Universal Z-Wave Sensor (Legacy)** model. Chooses which reading the device shows in the device list. |

Changing the native device, the Endpoint ID or the Sensor Type restarts the device so it listens in the right place. Renaming it does not.

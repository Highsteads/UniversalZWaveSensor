---
title: When something goes wrong
nav_order: 9
---

# When something goes wrong

Each section starts with what you see, then what it means and what to do.

## The Native Indigo Z-Wave Device list says "No native Z-Wave devices found"

The list shows every Z-Wave device in Indigo that has a node number, apart from this plugin's own devices.

- Check the sensor has been added to your Z-Wave network through Indigo, and that Indigo made a device for it.
- Check that device has a number in its **Address** column in Indigo's device list.

## Saving a device says it could not read a valid node number

The device you chose in **Native Indigo Z-Wave Device** has no usable node number. Choose the device Indigo made when the sensor was added to the network.

## Saving a device says "Endpoint must be blank (all endpoints) or a number 0-255"

**Endpoint ID** has something other than a whole number in it. Clear it, or put in the number of the part you want.

## A device never shows a reading

- **The sensor may not have sent anything yet.** A battery sensor only sends when something changes or when it wakes. Make the reading change, or press the sensor's button to wake it.
- **The model may not carry that reading.** A Generic Sensor does not show temperature, for example. Check the [Your devices](devices.md) page and make a device of the right model.
- **The Endpoint ID may be wrong.** Clear it so the device takes messages from every part, and see whether the reading arrives.
- **The sensor may not be sending it.** [One device instead of several](one-device-instead-of-several.md) shows how to check with debug logging, and what to do if nothing arrives.

## The Event Log says "Unhandled CC=0x..."

The sensor sent a message from a family the plugin does not read. The message is kept in the device's **Last Raw Report**. If it is a reading you want, run **Plugins → Universal Z-Wave Sensor → Generate Indigo Support Report** and post the report and that log line on the [Indigo forum](https://forums.indigodomo.com) or on [GitHub](https://github.com/Highsteads/UniversalZWaveSensor/issues). If the lines are only a nuisance, untick **Log unknown command classes** in the plugin's settings.

## The Event Log says "No report for ... — may be offline or out of range"

The sensor has sent nothing for longer than the **Stale threshold**, and its device is marked offline.

- For a battery sensor, this often only means it reports less often than the threshold allows. Raise **Stale threshold** in the plugin's settings.
- Otherwise check the sensor has power and a working battery, and that it is within reach of the rest of your Z-Wave network.

The device is set back to online, and the log says so, the next time the sensor sends anything.

## The Event Log says "No valid Node ID configured"

The device has lost its link to a native device. Open it, choose the device Indigo made in **Native Indigo Z-Wave Device**, and click **Save**.

## A device shows "reset locally"

The sensor has reported that it was reset to factory settings, which also takes it off your Z-Wave network. Add it to the network again through Indigo, then open each plugin device for it and choose the new native device Indigo makes.

## Temperatures show in the wrong unit

Change **Temperature unit** in **Plugins → Universal Z-Wave Sensor → Configure**. Each device shows the new unit from its sensor's next reading.

## A plug does not switch

The plugin passes the command to the device Indigo made for the plug. Check that device still exists and switches when you use it directly. If the Event Log says `no source device configured` or `source device ... not found`, open the plugin's device, choose the plug's native device again, and click **Save**.

## A lock shows "jammed"

The lock has reported that its bolt could not move freely. Check the door is shut properly and nothing is in the way, then lock or unlock it again.

## Still stuck?

Choose **Plugins → Universal Z-Wave Sensor → Show Plugin Info** and **Generate Indigo Support Report**, copy the lines they write to the Event Log, and post them on the [Indigo forum](https://forums.indigodomo.com) with a description of what you see. You can also [raise an issue on GitHub](https://github.com/Highsteads/UniversalZWaveSensor/issues).

---
title: Triggers and switching
nav_order: 6
---

# Triggers and switching

The plugin adds no actions or triggers of its own. Its devices are ordinary Indigo devices, so you use Indigo's own.

## Triggers

Create a trigger, set its type to **Device State Changed**, choose the plugin device, and pick the reading from the list. Every reading on the [Your devices](devices.md) page is there. Some examples:

| To do something when... | Trigger on |
|---|---|
| Motion is seen | **Motion** becomes true, on a Motion Sensor |
| A door opens | **Door/Window** becomes true, on a Contact Sensor |
| A room gets too warm | **Temperature** becomes greater than the value you choose |
| A battery needs changing | **Battery Low** becomes true |
| A leak is found | **Water Leak** becomes true, on a Generic Sensor |
| The door is unlocked | **Locked** becomes false, on a Lock |
| A button is pressed | **Last Scene** changes, or **Last Action** becomes `pressed`, on a Scene Controller |
| A sensor goes quiet | **Online** becomes false |

Pressing the same scene button twice in a row sets the same **Last Scene** each time, so to catch every press, trigger on **Scene Time**, which changes with every press, and check **Last Scene** in a condition.

## Switching a plug or relay

A **Plug / Relay** device answers Indigo's standard **Turn On**, **Turn Off** and **Toggle**, wherever you use them — the device list, a control page, a schedule, a trigger or an action group.

The plugin does not switch the plug itself. It passes each command to the device Indigo made for the plug, and Indigo sends it. When the plug reports that it has switched, the plugin's device follows. **Toggle** decides which way to switch from what the plugin's device shows.

If the device Indigo made has been deleted, the command goes nowhere and the Event Log says the source device was not found.

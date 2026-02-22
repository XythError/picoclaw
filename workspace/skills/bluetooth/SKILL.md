---
name: bluetooth
description: "Manage Bluetooth devices from the command line: scan for nearby devices, pair, connect, disconnect, and manage audio profiles. Use when the user needs to pair headphones/speakers, connect Bluetooth peripherals, troubleshoot Bluetooth connections, or automate Bluetooth tasks on Linux."
metadata: {"nanobot":{"emoji":"🔵","os":["linux"],"requires":{"bins":["bluetoothctl"]}}}
---

# Bluetooth Skill

Manage Bluetooth devices on Linux using `bluetoothctl` and related tools.

## Quick Start

```bash
# Enter interactive bluetoothctl shell
bluetoothctl

# Or run commands directly
bluetoothctl show                     # Controller info
bluetoothctl devices                  # List known devices
bluetoothctl paired-devices           # List paired devices
```

## Scanning & Discovering Devices

```bash
# Power on adapter and start scanning
bluetoothctl power on
bluetoothctl scan on

# Wait a few seconds, then list discovered devices
bluetoothctl devices

# Stop scan
bluetoothctl scan off
```

## Pairing a Device

```bash
# 1. Start scanning
bluetoothctl scan on

# 2. Note the device MAC address from scan output (e.g., AA:BB:CC:DD:EE:FF)
# 3. Pair
bluetoothctl pair AA:BB:CC:DD:EE:FF

# 4. Trust (auto-connect in future)
bluetoothctl trust AA:BB:CC:DD:EE:FF

# 5. Connect
bluetoothctl connect AA:BB:CC:DD:EE:FF
```

## Managing Connections

```bash
bluetoothctl connect AA:BB:CC:DD:EE:FF     # Connect to device
bluetoothctl disconnect AA:BB:CC:DD:EE:FF  # Disconnect
bluetoothctl remove AA:BB:CC:DD:EE:FF      # Unpair/remove device
bluetoothctl block AA:BB:CC:DD:EE:FF       # Block device
bluetoothctl unblock AA:BB:CC:DD:EE:FF     # Unblock device
```

## Audio Devices (via PulseAudio / PipeWire)

After connecting a Bluetooth audio device:

```bash
# List audio sinks (PulseAudio)
pactl list sinks short

# Set Bluetooth headphones as default sink
pactl set-default-sink bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink

# Switch active app to Bluetooth output
pactl list sink-inputs short
pactl move-sink-input <INPUT_ID> bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink

# PipeWire: use wpctl
wpctl status
wpctl set-default <SINK_ID>
```

## Auto-Connect Script

```bash
#!/usr/bin/env bash
# auto-connect-bt.sh — connect to trusted device if in range
DEVICE_MAC="AA:BB:CC:DD:EE:FF"

bluetoothctl power on

# Scan briefly
bluetoothctl scan on &
SCAN_PID=$!
sleep 5
kill $SCAN_PID 2>/dev/null

# Attempt connection
if bluetoothctl connect "$DEVICE_MAC" 2>&1 | grep -q "Connection successful"; then
    echo "Connected to $DEVICE_MAC"
else
    echo "Device not in range or connection failed"
fi
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Adapter not found | `hciconfig hci0 up` or check `rfkill list` |
| Device blocked | `rfkill unblock bluetooth` |
| Pairing fails | Run `bluetoothctl agent on` before pairing |
| Audio cuts out | Switch profile: `pactl set-card-profile bluez_card... a2dp_sink` |
| Device shows but won't connect | `bluetoothctl remove <MAC>` then re-pair |
| Service not running | `sudo systemctl start bluetooth` |

## Device Info

```bash
# Detailed info about a device
bluetoothctl info AA:BB:CC:DD:EE:FF

# Controller details
bluetoothctl show

# List all adapters
hciconfig -a
```

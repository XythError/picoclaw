---
name: termux-api
description: "Access Android device APIs from the Termux terminal using the termux-api package. Use when interacting with Android hardware or services: battery status, camera, clipboard, contacts, GPS/location, microphone recording, notifications, SMS, telephony, sensors, torch/flashlight, volume, vibration, wifi, and more."
metadata: {"nanobot":{"emoji":"📱","os":["android"],"requires":{"bins":["termux-battery-status"]},"install":[{"id":"termux-api-pkg","kind":"apt","package":"termux-api","bins":["termux-battery-status"],"label":"Install Termux:API package (pkg install termux-api)"}]}}
---

# Termux:API Skill

Use `termux-*` commands to interact with Android device APIs. Requires the **Termux:API** companion app installed from F-Droid (or Play Store) AND the `termux-api` package (`pkg install termux-api`).

## Quick Reference

```bash
# Battery
termux-battery-status            # JSON: health, percentage, plugged, status, temperature

# Camera
termux-camera-info               # List available cameras
termux-camera-photo /tmp/pic.jpg # Take photo (camera-id 0=back, 1=front)

# Clipboard
termux-clipboard-get             # Read clipboard text
termux-clipboard-set "text"      # Write to clipboard

# Contacts
termux-contact-list              # JSON list of contacts
termux-contact-list | jq '.[] | select(.name | test("Alice"))'

# Location / GPS
termux-location                  # Current GPS location (JSON)
termux-location -p gps -r once   # Force GPS (slower, more accurate)

# Microphone / Audio recording
termux-microphone-record -f /tmp/out.m4a -l 10   # Record 10 seconds
termux-microphone-record -q       # Query recording status
termux-microphone-record -q stop  # Stop recording

# Notifications
termux-notification --title "Hello" --content "World"
termux-notification --id 42 --title "Progress" --content "50%" --ongoing
termux-notification-remove 42

# SMS
termux-sms-list -t inbox -l 10   # Last 10 inbox messages
termux-sms-send -n "+1234567890" "Hello from Termux"

# Sensors
termux-sensor -l                 # List available sensors
termux-sensor -s "accelerometer" -n 5   # 5 readings from accelerometer

# Torch / Flashlight
termux-torch on
termux-torch off

# Volume
termux-volume                    # Current volume levels
termux-volume music 8            # Set music volume to 8

# Vibration
termux-vibrate -d 500            # Vibrate for 500 ms

# WiFi
termux-wifi-connectioninfo       # Current WiFi connection details
termux-wifi-scaninfo             # Scan for available networks

# Text-to-Speech
termux-tts-speak "Hello world"
termux-tts-speak -e com.google.android.tts -l en -r 1.0 "Hello"

# Share / Open
termux-share /tmp/file.txt       # Share file via Android share sheet
termux-open-url "https://example.com"
termux-open /tmp/file.pdf        # Open file with default app
```

## Working with JSON Output

All `termux-*` commands return JSON. Use `jq` to parse:

```bash
pkg install jq

# Battery percentage as plain number
termux-battery-status | jq '.percentage'

# GPS coordinates
termux-location | jq '{lat: .latitude, lon: .longitude}'

# Unread SMS count
termux-sms-list -t inbox | jq '[.[] | select(.read == false)] | length'
```

## Permissions

Android permissions must be granted to the **Termux:API** app:
- Location: `termux-location` requires Location permission
- Camera: `termux-camera-photo` requires Camera permission
- Contacts: `termux-contact-list` requires Contacts permission
- SMS: `termux-sms-list/send` requires SMS permission
- Microphone: `termux-microphone-record` requires Microphone permission

Grant via: Android Settings → Apps → Termux:API → Permissions

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found` | Run `pkg install termux-api` |
| Command hangs / no output | Termux:API companion app not installed or not running |
| Permission denied | Grant relevant Android permission to Termux:API app |
| Location returns null | Enable Location in Android settings; use `-p network` for faster result |
| SMS send fails | Check SMS permission and carrier restrictions |

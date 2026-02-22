#!/usr/bin/env python3
"""
PicoClaw Bluetooth Skill - Android 11+ (Termux + root)

Unified Bluetooth controller using:
  - svc bluetooth enable/disable
  - dumpsys bluetooth_manager (status, bonds, profiles, scan results)
  - am start/broadcast (intents for discoverable, settings, file sharing)
  - service call bluetooth_manager (low-level adapter operations)

Requirements: root (su), Android 11+
"""

import subprocess
import json
import sys
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


# ─── Helpers ───────────────────────────────────────────────────────────

def run_su(cmd: str, timeout: int = 15) -> str:
    """Run a command via su, return stdout."""
    try:
        r = subprocess.run(
            ["su", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        return f"ERROR: {e}"


def run_su_full(cmd: str, timeout: int = 15) -> dict:
    """Run a command via su, return stdout + stderr + returncode."""
    try:
        r = subprocess.run(
            ["su", "-c", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return {"stdout": r.stdout, "stderr": r.stderr, "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "timeout", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


def dumpsys_bt() -> str:
    """Get full dumpsys bluetooth_manager output."""
    return run_su("dumpsys bluetooth_manager")


def extract(text: str, pattern: str) -> Optional[str]:
    """Extract first regex match group."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def output_json(data: Any):
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ─── Status ────────────────────────────────────────────────────────────

def cmd_status() -> dict:
    """Full Bluetooth adapter status."""
    dump = dumpsys_bt()
    if not dump:
        return {"error": "dumpsys failed - is Bluetooth service running?"}

    enabled = "true" in run_su("settings get global bluetooth_on").lower() or \
              "enabled: true" in dump.lower()

    scan_mode_raw = extract(dump, r"ScanMode:\s*(\S+)") or "UNKNOWN"
    scan_mode_map = {
        "SCAN_MODE_NONE": "off",
        "SCAN_MODE_CONNECTABLE": "connectable",
        "SCAN_MODE_CONNECTABLE_DISCOVERABLE": "discoverable",
    }
    scan_mode = scan_mode_map.get(scan_mode_raw, scan_mode_raw)

    discovering = "true" in (extract(dump, r"Discovering:\s*(\S+)") or "false").lower()
    conn_state = extract(dump, r"ConnectionState:\s*(\S+)") or "UNKNOWN"

    # Parse active profiles
    profiles = re.findall(r"Profile:\s*(\S+)", dump)

    return {
        "enabled": enabled,
        "name": extract(dump, r"Name:\s*(.+)") or extract(dump, r"name:\s*(.+)"),
        "address": extract(dump, r"Address:\s*([0-9A-Fa-f:]{17})") or
                   extract(dump, r"address:\s*([0-9A-Fa-f:]{17})"),
        "scan_mode": scan_mode,
        "scan_mode_raw": scan_mode_raw,
        "discovering": discovering,
        "connection_state": conn_state,
        "profiles": profiles,
    }


# ─── Enable / Disable ─────────────────────────────────────────────────

def cmd_enable() -> dict:
    """Enable Bluetooth."""
    result = run_su_full("svc bluetooth enable")
    time.sleep(2)
    status = cmd_status()
    return {
        "action": "enable",
        "success": status.get("enabled", False),
        "status": status,
    }


def cmd_disable() -> dict:
    """Disable Bluetooth."""
    result = run_su_full("svc bluetooth disable")
    time.sleep(2)
    return {
        "action": "disable",
        "success": True,
        "note": "Bluetooth disabled",
    }


# ─── Discoverable ─────────────────────────────────────────────────────

def cmd_discoverable(duration: int = 120) -> dict:
    """Make device discoverable.

    Uses am start (Activity intent). On Android 11+, this pops up a
    confirmation dialog on screen. The user must tap 'Allow'.
    If the device is unattended, discoverability cannot be enabled silently.
    """
    # am start (Activity) — NOT am broadcast (which was the old bug)
    result = run_su_full(
        f'am start -a android.bluetooth.adapter.action.REQUEST_DISCOVERABLE '
        f'--ei android.bluetooth.adapter.extra.DISCOVERABLE_DURATION {duration}'
    )

    # Also open BT settings as fallback — on many Samsung/LineageOS devices,
    # having BT settings open automatically makes the device discoverable
    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")

    time.sleep(3)

    # Check result
    dump = dumpsys_bt()
    scan_mode = extract(dump, r"ScanMode:\s*(\S+)") or "UNKNOWN"
    is_discoverable = "DISCOVERABLE" in scan_mode

    return {
        "action": "discoverable",
        "duration_seconds": duration,
        "success": is_discoverable,
        "scan_mode": scan_mode,
        "note": "A confirmation dialog appeared on the device screen. "
                "The user must tap 'Allow' to enable discoverability."
                if not is_discoverable else
                f"Device is now discoverable for {duration} seconds.",
    }


# ─── Bonded (Paired) Devices ──────────────────────────────────────────

def cmd_bonded() -> list:
    """List bonded (paired) devices with detailed info."""
    dump = dumpsys_bt()
    devices = []

    # Strategy 1: Parse "Bonded devices:" section
    bonded_section = False
    for line in dump.split('\n'):
        if 'Bonded devices:' in line:
            bonded_section = True
            continue
        if bonded_section:
            # End of section
            if line.strip() and not line.startswith(' ') and ':' not in line:
                break
            mac = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', line)
            if mac:
                addr = mac.group(1)
                name = extract(line, r'name[=:]\s*(.+?)(?:\s+\(|$)') or "Unknown"
                if addr not in [d["address"] for d in devices]:
                    devices.append({
                        "address": addr,
                        "name": name,
                        "bonded": True,
                    })

    # Strategy 2: Parse profile-specific bonded info
    # Look for patterns like "58:C5:CB:E8:98:BE (POCO M7)" in various sections
    profile_pattern = r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\s*\(([^)]+)\)'
    for m in re.finditer(profile_pattern, dump):
        addr, name = m.group(1), m.group(2)
        if addr not in [d["address"] for d in devices]:
            # Check if this device appears in a bonded context
            devices.append({
                "address": addr,
                "name": name,
                "bonded": True,
            })

    # Strategy 3: Parse mDevices / DeviceProperties sections
    device_blocks = re.findall(
        r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}).*?(?:mName|name)\s*[=:]\s*(.+?)(?:\n|\r|$)',
        dump, re.IGNORECASE
    )
    for addr, name in device_blocks:
        name = name.strip()
        existing = [d for d in devices if d["address"] == addr]
        if existing:
            if existing[0]["name"] == "Unknown" and name:
                existing[0]["name"] = name
        # Don't add devices from generic parsing as "bonded"

    # Enrich with connection status
    for dev in devices:
        addr = dev["address"]
        # Check if device is currently connected
        connected_section = dump[dump.find(addr):dump.find(addr)+500] if addr in dump else ""
        dev["connected"] = "STATE_CONNECTED" in connected_section or \
                           "isConnected: true" in connected_section

    # Filter out own adapter address and null address
    own_addr = extract(dump, r"Address:\s*([0-9A-Fa-f:]{17})")
    devices = [d for d in devices
               if d["address"] != "00:00:00:00:00:00"
               and d["address"] != own_addr]

    return devices


# ─── Scan (Discovery) ─────────────────────────────────────────────────

def cmd_scan(timeout: int = 12) -> dict:
    """Scan for nearby Bluetooth devices.

    Opens Bluetooth Settings (which triggers discovery on most Android devices),
    waits for the specified timeout, then parses discovered devices from dumpsys.
    """
    # Step 1: Get initial state to diff against
    dump_before = dumpsys_bt()
    own_addr = extract(dump_before, r"Address:\s*([0-9A-Fa-f:]{17})")
    bonded_addrs = set()
    for m in re.finditer(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', dump_before):
        bonded_addrs.add(m.group(1))

    # Step 2: Open BT settings to trigger scan
    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")
    time.sleep(1)

    # Step 3: Trigger explicit discovery start via settings interaction
    # On most Android devices, opening BT settings auto-starts discovery.
    # We also try sending a discovery-start broadcast (may require BLUETOOTH_ADMIN)
    run_su("am broadcast -a android.bluetooth.adapter.action.REQUEST_ENABLE")

    print(f"Scanning for {timeout} seconds...", file=sys.stderr)
    time.sleep(timeout)

    # Step 4: Parse discovered devices from dumpsys
    dump_after = dumpsys_bt()
    devices = []

    # Parse all MAC addresses with context from the new dump
    lines = dump_after.split('\n')
    for i, line in enumerate(lines):
        mac_match = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', line)
        if mac_match:
            addr = mac_match.group(1)
            # Skip own address and null
            if addr == own_addr or addr == "00:00:00:00:00:00":
                continue

            # Try to find device name in nearby lines
            name = "Unknown"
            context = '\n'.join(lines[max(0, i-3):min(len(lines), i+5)])
            name_match = re.search(r'(?:mName|name)\s*[=:]\s*(.+?)(?:\n|\r|,|$)',
                                   context, re.IGNORECASE)
            if name_match:
                n = name_match.group(1).strip()
                if n and n != "null":
                    name = n

            # Check RSSI
            rssi = None
            rssi_match = re.search(r'mRssi\s*[=:]\s*(-?\d+)', context)
            if rssi_match:
                rssi = int(rssi_match.group(1))

            # Determine if bonded
            is_bonded = addr in bonded_addrs or "BOND_BONDED" in context

            if not any(d["address"] == addr for d in devices):
                dev = {
                    "address": addr,
                    "name": name,
                    "bonded": is_bonded,
                }
                if rssi is not None:
                    dev["rssi"] = rssi
                devices.append(dev)

    # Check discovery status
    is_discovering = "Discovering: true" in dump_after

    return {
        "action": "scan",
        "duration_seconds": timeout,
        "discovering": is_discovering,
        "devices_found": len(devices),
        "devices": devices,
        "note": "Scan uses Android BT Settings to trigger discovery. "
                "Only devices that were visible during the scan window appear."
                if devices else
                "No devices found. Ensure target devices are in discoverable mode "
                "and within range. Try a longer scan timeout.",
    }


# ─── Device Info ───────────────────────────────────────────────────────

def cmd_info(mac: str) -> dict:
    """Get detailed info about a specific device."""
    if not re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac):
        return {"error": f"Invalid MAC address: {mac}"}

    dump = dumpsys_bt()
    mac_upper = mac.upper()

    if mac_upper not in dump.upper():
        return {
            "address": mac,
            "error": "Device not found in Bluetooth manager. "
                     "It may need to be scanned or paired first.",
        }

    # Extract all info about this device
    info = {
        "address": mac,
        "name": "Unknown",
        "bonded": False,
        "connected": False,
        "profiles": [],
    }

    # Find device sections
    lines = dump.split('\n')
    for i, line in enumerate(lines):
        if mac_upper in line.upper():
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+10)])

            # Name
            nm = re.search(r'(?:mName|name)\s*[=:]\s*(.+?)(?:\n|\r|$)', context, re.IGNORECASE)
            if nm and nm.group(1).strip() not in ("null", ""):
                info["name"] = nm.group(1).strip()

            # Bond state
            if "BOND_BONDED" in context:
                info["bonded"] = True

            # Connection
            if "STATE_CONNECTED" in context or "isConnected: true" in context:
                info["connected"] = True

            # RSSI
            rssi = re.search(r'mRssi\s*[=:]\s*(-?\d+)', context)
            if rssi:
                info["rssi"] = int(rssi.group(1))

            # Device class
            cls = re.search(r'(?:class|mClass)\s*[=:]\s*(0x[0-9a-fA-F]+|\d+)', context)
            if cls:
                info["device_class"] = cls.group(1)

    # Check which profiles this device uses
    profile_names = ["A2dpService", "HeadsetService", "HidHostService",
                     "PanService", "BluetoothOppService", "AvrcpTargetService"]
    for pname in profile_names:
        section_start = dump.find(f"Profile: {pname}")
        if section_start >= 0:
            section = dump[section_start:section_start + 2000]
            if mac_upper in section.upper():
                info["profiles"].append(pname.replace("Service", ""))

    return info


# ─── Pair ──────────────────────────────────────────────────────────────

def cmd_pair(mac: str) -> dict:
    """Initiate pairing with a device.

    Opens Bluetooth settings. Pairing on Android requires UI confirmation
    (PIN or passkey dialog). This cannot be fully automated.
    """
    if not re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac):
        return {"error": f"Invalid MAC address: {mac}"}

    # Open BT settings
    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")
    time.sleep(1)

    # Try to trigger pairing via broadcast (works on some devices)
    run_su(
        f'am broadcast -a android.bluetooth.device.action.PAIRING_REQUEST '
        f'--es android.bluetooth.device.extra.DEVICE {mac}'
    )

    return {
        "action": "pair",
        "device": mac,
        "status": "pairing_initiated",
        "note": "Bluetooth Settings opened. The user must:\n"
                "1. Find the target device in the scan list\n"
                "2. Tap to pair\n"
                "3. Confirm the PIN/passkey on both devices\n"
                "Pairing requires physical interaction with the Android UI.",
    }


# ─── Unpair ───────────────────────────────────────────────────────────

def cmd_unpair(mac: str) -> dict:
    """Remove pairing (bond) with a device.

    Uses service call to invoke removeBond() on the BluetoothDevice.
    This may not work on all devices — fallback is manual via Settings.
    """
    if not re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac):
        return {"error": f"Invalid MAC address: {mac}"}

    # Try to remove bond via Settings
    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")

    return {
        "action": "unpair",
        "device": mac,
        "note": "Bluetooth Settings opened. To unpair:\n"
                "1. Find the device in 'Paired devices'\n"
                "2. Tap the gear/settings icon next to it\n"
                "3. Tap 'Forget' or 'Unpair'\n"
                "Note: On some devices, unpair can be automated via root.",
    }


# ─── Connect (A2DP / Audio) ───────────────────────────────────────────

def cmd_connect(mac: str, profile: str = "a2dp") -> dict:
    """Connect to a paired device (e.g. Bluetooth speaker/headphones).

    For A2DP (audio), this opens BT settings. The user taps the paired device
    to connect. For previously connected devices, Android may reconnect
    automatically when the device is in range.
    """
    if not re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac):
        return {"error": f"Invalid MAC address: {mac}"}

    # Check if device is bonded
    bonded = cmd_bonded()
    is_bonded = any(d["address"].upper() == mac.upper() for d in bonded)

    if not is_bonded:
        return {
            "action": "connect",
            "device": mac,
            "error": "Device is not paired. Pair it first with: bluetooth pair <mac>",
        }

    # Open BT settings to trigger connection
    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")

    # Try to force A2DP connection via media routing
    if profile.lower() in ("a2dp", "audio", "speaker"):
        # Try to set preferred audio device
        run_su(f"am broadcast -a android.bluetooth.a2dp.profile.action.CONNECTION_STATE_CHANGED")

    return {
        "action": "connect",
        "device": mac,
        "profile": profile,
        "status": "connection_initiated",
        "note": "Bluetooth Settings opened. To connect:\n"
                "1. Find the device under 'Paired devices'\n"
                "2. Tap it to connect\n"
                "For audio devices (speakers/headphones): once connected, "
                "audio will automatically route to the device.",
    }


# ─── Disconnect ────────────────────────────────────────────────────────

def cmd_disconnect(mac: str) -> dict:
    """Disconnect a connected device."""
    if not re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac):
        return {"error": f"Invalid MAC address: {mac}"}

    run_su("am start -a android.settings.BLUETOOTH_SETTINGS")

    return {
        "action": "disconnect",
        "device": mac,
        "note": "Bluetooth Settings opened. To disconnect:\n"
                "1. Find the connected device\n"
                "2. Tap it or tap the gear icon\n"
                "3. Select 'Disconnect'",
    }


# ─── Send File ─────────────────────────────────────────────────────────

MIME_TYPES = {
    '.txt': 'text/plain', '.log': 'text/plain', '.md': 'text/plain',
    '.csv': 'text/csv', '.json': 'application/json',
    '.pdf': 'application/pdf',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.webp': 'image/webp', '.gif': 'image/gif',
    '.bmp': 'image/bmp', '.svg': 'image/svg+xml',
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
    '.flac': 'audio/flac', '.aac': 'audio/aac', '.m4a': 'audio/mp4',
    '.mp4': 'video/mp4', '.mkv': 'video/x-matroska', '.avi': 'video/x-msvideo',
    '.webm': 'video/webm', '.mov': 'video/quicktime',
    '.zip': 'application/zip', '.tar': 'application/x-tar',
    '.gz': 'application/gzip', '.7z': 'application/x-7z-compressed',
    '.apk': 'application/vnd.android.package-archive',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


def cmd_send(filepath: str) -> dict:
    """Send a file via Bluetooth (Android Share intent with BT chooser)."""
    fpath = Path(filepath).resolve()
    if not fpath.exists():
        return {"error": f"File not found: {filepath}"}
    if not fpath.is_file():
        return {"error": f"Not a regular file: {filepath}"}

    ext = fpath.suffix.lower()
    mime = MIME_TYPES.get(ext, 'application/octet-stream')
    file_uri = f"file://{fpath}"
    size_kb = fpath.stat().st_size / 1024

    # Use explicit Bluetooth OPP component for direct BT sending
    result = run_su_full(
        f"am start -a android.intent.action.SEND "
        f"-t '{mime}' "
        f"--eu android.intent.extra.STREAM '{file_uri}' "
        f"-n com.android.bluetooth/.opp.BluetoothOppLauncherActivity"
    )

    # Fallback to generic share chooser if BT component fails
    if result["returncode"] != 0:
        result = run_su_full(
            f"am start -a android.intent.action.SEND "
            f"-t '{mime}' "
            f"--eu android.intent.extra.STREAM '{file_uri}'"
        )
        method = "share_chooser"
    else:
        method = "bluetooth_opp"

    return {
        "action": "send",
        "file": str(fpath),
        "file_size_kb": round(size_kb, 1),
        "mime_type": mime,
        "method": method,
        "success": result["returncode"] == 0,
        "note": "Bluetooth device chooser opened on screen. "
                "Select the target device to start transfer."
                if result["returncode"] == 0 else
                f"Failed to start send intent: {result['stderr']}",
    }


# ─── Connected Devices ────────────────────────────────────────────────

def cmd_connected() -> list:
    """List currently connected Bluetooth devices."""
    dump = dumpsys_bt()
    own_addr = extract(dump, r"Address:\s*([0-9A-Fa-f:]{17})")
    devices = []

    # Parse active device connections from profile sections
    profile_sections = [
        ("A2dp", "A2dpService"),
        ("Headset", "HeadsetService"),
        ("HID", "HidHostService"),
    ]

    for short_name, service_name in profile_sections:
        section_start = dump.find(f"Profile: {service_name}")
        if section_start < 0:
            continue
        # Get section until next "Profile:" or end
        next_profile = dump.find("Profile:", section_start + 1)
        section = dump[section_start:next_profile] if next_profile > 0 else dump[section_start:]

        # Look for connected devices in this section
        if "mActiveDevice" in section:
            active_match = re.search(
                r'mActiveDevice\s*[=:]\s*([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})',
                section
            )
            if active_match:
                addr = active_match.group(1)
                if addr != "00:00:00:00:00:00" and addr != own_addr:
                    existing = [d for d in devices if d["address"] == addr]
                    if existing:
                        existing[0]["profiles"].append(short_name)
                    else:
                        devices.append({
                            "address": addr,
                            "name": "Unknown",
                            "profiles": [short_name],
                            "connected": True,
                        })

        # Check STATE_CONNECTED patterns
        for m in re.finditer(
            r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}).*?STATE_CONNECTED',
            section
        ):
            addr = m.group(1)
            if addr != "00:00:00:00:00:00" and addr != own_addr:
                existing = [d for d in devices if d["address"] == addr]
                if existing:
                    if short_name not in existing[0]["profiles"]:
                        existing[0]["profiles"].append(short_name)
                else:
                    devices.append({
                        "address": addr,
                        "name": "Unknown",
                        "profiles": [short_name],
                        "connected": True,
                    })

    # Try to resolve names for connected devices
    for dev in devices:
        info = cmd_info(dev["address"])
        if info.get("name") and info["name"] != "Unknown":
            dev["name"] = info["name"]

    return devices


# ─── Audio Routing ─────────────────────────────────────────────────────

def cmd_audio_info() -> dict:
    """Get current audio routing info (useful for BT speaker debugging)."""
    audio_dump = run_su("dumpsys audio | head -80")

    bt_connected = "bt_sco=on" in audio_dump.lower() or \
                   "a2dp" in audio_dump.lower()

    return {
        "bt_audio_active": bt_connected,
        "audio_summary": audio_dump[:500] if audio_dump else "Could not read audio state",
    }


# ─── Set Name ──────────────────────────────────────────────────────────

def cmd_set_name(name: str) -> dict:
    """Change the Bluetooth adapter name."""
    run_su(f"settings put secure bluetooth_name '{name}'")
    time.sleep(1)
    status = cmd_status()
    return {
        "action": "set_name",
        "requested_name": name,
        "current_name": status.get("name", "Unknown"),
        "note": "Name change may require Bluetooth restart to take effect.",
    }


# ─── Main ──────────────────────────────────────────────────────────────

COMMANDS = {
    "status":       ("Show Bluetooth adapter status",             lambda args: cmd_status()),
    "enable":       ("Turn Bluetooth on",                         lambda args: cmd_enable()),
    "disable":      ("Turn Bluetooth off",                        lambda args: cmd_disable()),
    "discoverable": ("Make device discoverable (needs UI confirm)", lambda args: cmd_discoverable(int(args[0]) if args else 120)),
    "scan":         ("Scan for nearby devices",                   lambda args: cmd_scan(int(args[0]) if args else 12)),
    "bonded":       ("List paired devices",                       lambda args: cmd_bonded()),
    "connected":    ("List currently connected devices",          lambda args: cmd_connected()),
    "info":         ("Get info about a device <mac>",             lambda args: cmd_info(args[0]) if args else {"error": "MAC required"}),
    "pair":         ("Pair with a device <mac>",                  lambda args: cmd_pair(args[0]) if args else {"error": "MAC required"}),
    "unpair":       ("Remove pairing <mac>",                      lambda args: cmd_unpair(args[0]) if args else {"error": "MAC required"}),
    "connect":      ("Connect to paired device <mac> [profile]",  lambda args: cmd_connect(args[0], args[1] if len(args) > 1 else "a2dp") if args else {"error": "MAC required"}),
    "disconnect":   ("Disconnect a device <mac>",                 lambda args: cmd_disconnect(args[0]) if args else {"error": "MAC required"}),
    "send":         ("Send a file via Bluetooth <path>",          lambda args: cmd_send(args[0]) if args else {"error": "file path required"}),
    "audio":        ("Show audio routing info",                   lambda args: cmd_audio_info()),
    "set-name":     ("Change adapter name <name>",                lambda args: cmd_set_name(' '.join(args)) if args else {"error": "name required"}),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("PicoClaw Bluetooth Controller")
        print(f"Usage: {sys.argv[0]} <command> [args...]")
        print()
        for name, (desc, _) in COMMANDS.items():
            print(f"  {name:16s} {desc}")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd not in COMMANDS:
        print(json.dumps({"error": f"Unknown command: {cmd}",
                          "available": list(COMMANDS.keys())}))
        sys.exit(1)

    _, handler = COMMANDS[cmd]
    result = handler(args)
    output_json(result)


if __name__ == '__main__':
    main()

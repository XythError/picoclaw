#!/usr/bin/env python3
"""
termux-api.py: Zuverlässiger Wrapper für Termux:API.
Gibt dem Agenten sicheren Zugriff auf Android-Hardware und System-APIs.
Alle Befehle mit Timeout, strukturiertem Output und Fehlerbehandlung.

Getestet auf: Samsung Galaxy Tab A SM-T580, Android 11, Termux 0.118.1
"""
import subprocess
import json
import sys
import argparse
from typing import Optional

# Termux-API Binaries liegen im Termux-Prefix
API_PREFIX = "/data/data/com.termux/files/usr/bin"


def _run_api(cmd: list, timeout: int = 10, stdin_data: str = None) -> dict:
    """Führt einen Termux-API Befehl aus mit Timeout und Fehlerbehandlung."""
    # Absolute Pfade für den ersten Befehl
    full_cmd = [f"{API_PREFIX}/{cmd[0]}"] + cmd[1:]

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_data
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return {"success": False, "error": stderr or f"Exit code {result.returncode}"}

        # Versuche JSON zu parsen
        if output:
            try:
                data = json.loads(output)
                # Prüfe auf API-Permission-Fehler
                if isinstance(data, dict) and "error" in data:
                    return {"success": False, "error": data["error"]}
                return {"success": True, "data": data}
            except json.JSONDecodeError:
                return {"success": True, "data": output}
        return {"success": True, "data": None}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout nach {timeout}s"}
    except FileNotFoundError:
        return {"success": False, "error": f"Befehl nicht gefunden: {cmd[0]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# HARDWARE & SYSTEM
# ============================================================

def cmd_battery(args) -> dict:
    """Batterie-Status: Ladung, Temperatur, Stromquelle."""
    return _run_api(["termux-battery-status"])


def cmd_wifi(args) -> dict:
    """WiFi-Verbindungsinfo: IP, SSID, Signalstärke, Frequenz."""
    return _run_api(["termux-wifi-connectioninfo"])


def cmd_wifi_scan(args) -> dict:
    """WiFi-Netzwerke in der Umgebung scannen."""
    return _run_api(["termux-wifi-scaninfo"], timeout=15)


def cmd_audio(args) -> dict:
    """Audio-Systeminformationen."""
    return _run_api(["termux-audio-info"])


def cmd_volume(args) -> dict:
    """Lautstärke anzeigen oder setzen.
    Ohne Argumente: alle Streams anzeigen.
    Mit --stream und --value: Lautstärke setzen."""
    if args.stream and args.value is not None:
        return _run_api(["termux-volume", args.stream, str(args.value)])
    return _run_api(["termux-volume"])


def cmd_brightness(args) -> dict:
    """Bildschirmhelligkeit setzen (auto | 0-255)."""
    val = args.value if args.value else "auto"
    return _run_api(["termux-brightness", val])


def cmd_torch(args) -> dict:
    """Taschenlampe ein-/ausschalten (on|off)."""
    state = args.state if args.state else "on"
    return _run_api(["termux-torch", state])


def cmd_vibrate(args) -> dict:
    """Gerät vibrieren lassen."""
    duration = str(args.duration) if args.duration else "500"
    return _run_api(["termux-vibrate", "-d", duration])


def cmd_sensor_list(args) -> dict:
    """Verfügbare Sensoren auflisten."""
    return _run_api(["termux-sensor", "-l"])


def cmd_sensor_read(args) -> dict:
    """Sensor einmalig auslesen."""
    sensor = args.sensor if args.sensor else "all"
    return _run_api(["termux-sensor", "-s", sensor, "-n", "1"], timeout=10)


def cmd_camera_info(args) -> dict:
    """Kamera-Informationen (verfügbare Kameras, Auflösungen)."""
    return _run_api(["termux-camera-info"])


def cmd_camera_photo(args) -> dict:
    """Foto aufnehmen und speichern."""
    cam_id = str(args.camera) if args.camera is not None else "0"
    output = args.output if args.output else "/data/data/com.termux/files/home/.picoclaw/workspace/cloud/photo.jpg"
    return _run_api(["termux-camera-photo", "-c", cam_id, output], timeout=15)


# ============================================================
# BENACHRICHTIGUNGEN & UI
# ============================================================

def cmd_toast(args) -> dict:
    """Toast-Nachricht auf dem Bildschirm anzeigen."""
    cmd = ["termux-toast"]
    if args.position:
        cmd.extend(["-g", args.position])
    if args.background:
        cmd.extend(["-b", args.background])
    cmd.append(args.text)
    return _run_api(cmd)


def cmd_notification(args) -> dict:
    """Android-Benachrichtigung erstellen."""
    cmd = ["termux-notification", "--title", args.title]
    if args.content:
        cmd.extend(["--content", args.content])
    if args.id:
        cmd.extend(["--id", args.id])
    if args.priority:
        cmd.extend(["--priority", args.priority])
    return _run_api(cmd)


def cmd_notification_remove(args) -> dict:
    """Benachrichtigung entfernen."""
    return _run_api(["termux-notification-remove", args.id])


def cmd_notification_list(args) -> dict:
    """Aktive Benachrichtigungen auflisten."""
    return _run_api(["termux-notification-list"], timeout=20)


# ============================================================
# CLIPBOARD
# ============================================================

def cmd_clipboard_get(args) -> dict:
    """Zwischenablage-Inhalt lesen."""
    return _run_api(["termux-clipboard-get"])


def cmd_clipboard_set(args) -> dict:
    """Text in Zwischenablage kopieren."""
    return _run_api(["termux-clipboard-set", args.text])


# ============================================================
# TELEFONIE (WiFi-only Tablet: eingeschränkt)
# ============================================================

def cmd_telephony(args) -> dict:
    """Telefonie-Geräteinformationen."""
    return _run_api(["termux-telephony-deviceinfo"])


def cmd_contacts(args) -> dict:
    """Kontaktliste abrufen."""
    return _run_api(["termux-contact-list"])


# ============================================================
# MEDIA
# ============================================================

def cmd_media_scan(args) -> dict:
    """Datei in Android Media-Scanner registrieren."""
    return _run_api(["termux-media-scan", args.file])


# ============================================================
# WAKE LOCK
# ============================================================

def cmd_wake_lock(args) -> dict:
    """Wake-Lock aktivieren (verhindert CPU-Schlaf)."""
    return _run_api(["termux-wake-lock"])


def cmd_wake_unlock(args) -> dict:
    """Wake-Lock deaktivieren."""
    return _run_api(["termux-wake-unlock"])


# ============================================================
# TTS (Text-to-Speech)
# ============================================================

def cmd_tts_speak(args) -> dict:
    """Text vorlesen (TTS). Erfordert eine TTS-Engine auf dem Gerät."""
    cmd = ["termux-tts-speak"]
    if args.rate:
        cmd.extend(["-r", str(args.rate)])
    cmd.append(args.text)
    return _run_api(cmd, timeout=30)


def cmd_tts_engines(args) -> dict:
    """Verfügbare TTS-Engines auflisten."""
    return _run_api(["termux-tts-engines"])


# ============================================================
# INFRARED (IR-Blaster)
# ============================================================

def cmd_ir_frequencies(args) -> dict:
    """IR-Blaster: Unterstützte Frequenzbereiche."""
    return _run_api(["termux-infrared-frequencies"])


def cmd_ir_transmit(args) -> dict:
    """IR-Signal senden. Frequenz in Hz, Pattern als kommagetrennte Werte."""
    return _run_api(["termux-infrared-transmit", "-f", str(args.frequency)] + args.pattern.split(","))


# ============================================================
# DIALOG (interaktive Eingabe - nützlich für Automatisierung)
# ============================================================

def cmd_dialog(args) -> dict:
    """Interaktiven Dialog anzeigen (confirm/text/spinner/date/time)."""
    cmd = ["termux-dialog", args.widget]
    if args.title:
        cmd.extend(["-t", args.title])
    if args.values:
        cmd.extend(["-v", args.values])
    return _run_api(cmd, timeout=60)


# ============================================================
# SYSTEM INFO
# ============================================================

def cmd_info(args) -> dict:
    """Umfassende Geräte-/System-Info sammeln."""
    result = {}
    for name, apicmd in [
        ("battery", ["termux-battery-status"]),
        ("wifi", ["termux-wifi-connectioninfo"]),
        ("volume", ["termux-volume"]),
        ("audio", ["termux-audio-info"]),
    ]:
        r = _run_api(apicmd, timeout=8)
        result[name] = r.get("data") if r["success"] else r.get("error")
    return {"success": True, "data": result}


# ============================================================
# CLI
# ============================================================

def main():
    # --json kann vor oder nach dem Subcommand stehen
    json_output = "--json" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--json"]

    parser = argparse.ArgumentParser(
        description="termux-api: Android-Hardware und System-APIs für PicoClaw",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Beispiele:
  %(prog)s battery                        # Batterie-Status
  %(prog)s wifi                           # WiFi-Info
  %(prog)s toast "Hallo Welt"             # Toast anzeigen
  %(prog)s notification --title Test      # Benachrichtigung
  %(prog)s torch on                       # Taschenlampe an
  %(prog)s volume --stream music --value 10  # Musik-Lautstärke
  %(prog)s photo --camera 0 --output /path/foto.jpg  # Foto
  %(prog)s info                           # Alles auf einen Blick
  --json kann vor oder nach dem Befehl stehen
"""
    )
    sub = parser.add_subparsers(dest="command", help="API-Befehl")

    # --- Hardware & System ---
    sub.add_parser("battery", help="Batterie-Status")
    sub.add_parser("wifi", help="WiFi-Verbindungsinfo")
    sub.add_parser("wifi-scan", help="WiFi-Netzwerke scannen")
    sub.add_parser("audio", help="Audio-Systeminformationen")

    p = sub.add_parser("volume", help="Lautstärke anzeigen/setzen")
    p.add_argument("--stream", choices=["call", "system", "ring", "music", "alarm", "notification"])
    p.add_argument("--value", type=int, help="Lautstärke-Wert")

    p = sub.add_parser("brightness", help="Bildschirmhelligkeit (auto|0-255)")
    p.add_argument("value", nargs="?", default="auto")

    p = sub.add_parser("torch", help="Taschenlampe (on|off)")
    p.add_argument("state", nargs="?", default="on", choices=["on", "off"])

    p = sub.add_parser("vibrate", help="Vibrieren")
    p.add_argument("--duration", "-d", type=int, default=500, help="Dauer in ms")

    sub.add_parser("sensor-list", help="Sensoren auflisten")

    p = sub.add_parser("sensor-read", help="Sensor auslesen")
    p.add_argument("--sensor", "-s", default="all", help="Sensorname oder 'all'")

    sub.add_parser("camera-info", help="Kamera-Informationen")

    p = sub.add_parser("photo", help="Foto aufnehmen")
    p.add_argument("--camera", "-c", type=int, default=0, help="Kamera-ID (0=back, 1=front)")
    p.add_argument("--output", "-o", help="Ausgabe-Datei")

    # --- Benachrichtigungen & UI ---
    p = sub.add_parser("toast", help="Toast-Nachricht")
    p.add_argument("text", help="Anzuzeigender Text")
    p.add_argument("--position", "-g", choices=["top", "middle", "bottom"])
    p.add_argument("--background", "-b", help="Hintergrundfarbe")

    p = sub.add_parser("notification", help="Benachrichtigung erstellen")
    p.add_argument("--title", "-t", required=True, help="Titel")
    p.add_argument("--content", "-c", help="Inhalt")
    p.add_argument("--id", help="Benachrichtigungs-ID")
    p.add_argument("--priority", choices=["default", "high", "low", "max", "min"])

    p = sub.add_parser("notification-remove", help="Benachrichtigung entfernen")
    p.add_argument("id", help="Benachrichtigungs-ID")

    sub.add_parser("notification-list", help="Benachrichtigungen auflisten")

    # --- Clipboard ---
    sub.add_parser("clipboard-get", help="Zwischenablage lesen")

    p = sub.add_parser("clipboard-set", help="In Zwischenablage kopieren")
    p.add_argument("text", help="Text")

    # --- Telefonie ---
    sub.add_parser("telephony", help="Telefonie-Geräteinformationen")
    sub.add_parser("contacts", help="Kontakte auflisten")

    # --- Media ---
    p = sub.add_parser("media-scan", help="Datei im Media-Scanner registrieren")
    p.add_argument("file", help="Dateipfad")

    # --- Wake Lock ---
    sub.add_parser("wake-lock", help="Wake-Lock aktivieren")
    sub.add_parser("wake-unlock", help="Wake-Lock deaktivieren")

    # --- TTS ---
    p = sub.add_parser("tts-speak", help="Text vorlesen (TTS)")
    p.add_argument("text", help="Vorzulesender Text")
    p.add_argument("--rate", type=float, help="Sprechgeschwindigkeit")

    sub.add_parser("tts-engines", help="TTS-Engines auflisten")

    # --- IR ---
    sub.add_parser("ir-frequencies", help="IR-Frequenzbereiche")

    p = sub.add_parser("ir-transmit", help="IR-Signal senden")
    p.add_argument("--frequency", "-f", type=int, required=True, help="Frequenz in Hz")
    p.add_argument("--pattern", "-p", required=True, help="Pattern (kommagetrennt)")

    # --- Dialog ---
    p = sub.add_parser("dialog", help="Interaktiven Dialog anzeigen")
    p.add_argument("widget", choices=["confirm", "text", "spinner", "date", "time", "counter", "speech"])
    p.add_argument("--title", "-t")
    p.add_argument("--values", "-v", help="Werte (kommagetrennt, für spinner)")

    # --- System Info ---
    sub.add_parser("info", help="Umfassende Geräte-Info")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Befehl ausführen
    dispatch = {
        "battery": cmd_battery,
        "wifi": cmd_wifi,
        "wifi-scan": cmd_wifi_scan,
        "audio": cmd_audio,
        "volume": cmd_volume,
        "brightness": cmd_brightness,
        "torch": cmd_torch,
        "vibrate": cmd_vibrate,
        "sensor-list": cmd_sensor_list,
        "sensor-read": cmd_sensor_read,
        "camera-info": cmd_camera_info,
        "photo": cmd_camera_photo,
        "toast": cmd_toast,
        "notification": cmd_notification,
        "notification-remove": cmd_notification_remove,
        "notification-list": cmd_notification_list,
        "clipboard-get": cmd_clipboard_get,
        "clipboard-set": cmd_clipboard_set,
        "telephony": cmd_telephony,
        "contacts": cmd_contacts,
        "media-scan": cmd_media_scan,
        "wake-lock": cmd_wake_lock,
        "wake-unlock": cmd_wake_unlock,
        "tts-speak": cmd_tts_speak,
        "tts-engines": cmd_tts_engines,
        "ir-frequencies": cmd_ir_frequencies,
        "ir-transmit": cmd_ir_transmit,
        "dialog": cmd_dialog,
        "info": cmd_info,
    }

    result = dispatch[args.command](args)

    # Output
    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if not result.get("success"):
            print(f"FEHLER: {result.get('error', 'unbekannt')}", file=sys.stderr)
            sys.exit(1)

        data = result.get("data")
        if data is None:
            print("OK")
        elif isinstance(data, str):
            print(data)
        elif isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(data)


if __name__ == "__main__":
    main()

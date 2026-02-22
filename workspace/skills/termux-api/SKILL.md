---
name: termux-api
description: Android-Hardware und System-APIs (Batterie, WiFi, Sensoren, Kamera, Benachrichtigungen, Clipboard, Helligkeit, Taschenlampe). Kein su noetig.
---

# Termux API Skill

Android-Hardware und System-APIs für PicoClaw.

## Voraussetzungen
- Termux:API App installiert (com.termux.api)
- Alle Permissions per root gesetzt (Kamera, Kontakte, Location, SMS, etc.)
- Kein `su` nötig — die APIs laufen über die Termux:API Android-App

## Nutzung

```bash
python3 skills/termux-api/scripts/termux-api.py <befehl> [optionen]
```

## Verfügbare Befehle

### Hardware & System
| Befehl | Beschreibung | Beispiel |
|--------|-------------|----------|
| `battery` | Batterie-Status (Ladung, Temp, Quelle) | `python3 skills/termux-api/scripts/termux-api.py battery` |
| `wifi` | WiFi-Verbindung (IP, SSID, Signal) | `python3 skills/termux-api/scripts/termux-api.py wifi` |
| `wifi-scan` | WiFi-Netzwerke scannen | `python3 skills/termux-api/scripts/termux-api.py wifi-scan` |
| `audio` | Audio-Systeminformationen | `python3 skills/termux-api/scripts/termux-api.py audio` |
| `volume` | Lautstärke anzeigen | `python3 skills/termux-api/scripts/termux-api.py volume` |
| `volume --stream music --value 10` | Lautstärke setzen | Streams: call, system, ring, music, alarm, notification |
| `brightness auto` | Helligkeit (auto oder 0-255) | `python3 skills/termux-api/scripts/termux-api.py brightness 128` |
| `torch on/off` | Taschenlampe | `python3 skills/termux-api/scripts/termux-api.py torch on` |
| `vibrate --duration 500` | Vibrieren (ms) | `python3 skills/termux-api/scripts/termux-api.py vibrate -d 1000` |
| `sensor-list` | Verfügbare Sensoren | Accelerometer, Light, Grip |
| `sensor-read --sensor <name>` | Sensor auslesen | `python3 skills/termux-api/scripts/termux-api.py sensor-read -s "CM3323E Light"` |
| `camera-info` | Kamera-Details | 2 Kameras: 0=back (3264x2448), 1=front |
| `photo --camera 0 --output pfad.jpg` | Foto aufnehmen | `python3 skills/termux-api/scripts/termux-api.py photo -c 0 -o cloud/foto.jpg` |

### Benachrichtigungen & UI
| Befehl | Beschreibung |
|--------|-------------|
| `toast "Text"` | Toast-Nachricht auf Bildschirm |
| `notification --title X --content Y --id Z` | Android-Benachrichtigung |
| `notification-remove <id>` | Benachrichtigung entfernen |
| `notification-list` | Aktive Benachrichtigungen |

### Clipboard
| Befehl | Beschreibung |
|--------|-------------|
| `clipboard-get` | Zwischenablage lesen |
| `clipboard-set "Text"` | In Zwischenablage kopieren |

### Media & System
| Befehl | Beschreibung |
|--------|-------------|
| `media-scan <datei>` | Datei im Android Media-Scanner registrieren |
| `wake-lock` | CPU-Schlaf verhindern |
| `wake-unlock` | Wake-Lock aufheben |
| `telephony` | Telefonie-Infos (WiFi-only Tablet) |
| `contacts` | Kontaktliste |

### TTS (Text-to-Speech)
| Befehl | Beschreibung |
|--------|-------------|
| `tts-speak "Text" --rate 1.0` | Text vorlesen |
| `tts-engines` | Verfügbare TTS-Engines |

### IR-Blaster
| Befehl | Beschreibung |
|--------|-------------|
| `ir-frequencies` | Unterstützte IR-Frequenzen |
| `ir-transmit -f 38000 -p "100,50,100,50"` | IR-Signal senden |

### System-Übersicht
| Befehl | Beschreibung |
|--------|-------------|
| `info` | Batterie + WiFi + Volume + Audio auf einen Blick |

## Flags
- `--json` — Immer JSON-Output (für Automatisierung)

## Wichtige Hinweise
- **Kein su nötig!** Die API läuft über die Android-App, nicht über Shell-Befehle
- **Location funktioniert NICHT** — WiFi-only Tablet hat kein GPS
- **TTS**: Nur wenn eine TTS-Engine auf dem Gerät installiert ist
- **Timeouts**: Alle Befehle haben Timeouts (8-60s), hängen sich nie auf
- **Fotos**: Default-Speicherort ist `cloud/photo.jpg` (wird via Nextcloud gesynct)

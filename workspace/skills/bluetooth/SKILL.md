---
name: bluetooth
description: Bluetooth-Steuerung fuer Android (Termux + root). Ein/Aus, Scan, Pairing, Dateiversand, A2DP-Lautsprecher, Status.
---

# Bluetooth Controller

Unified Bluetooth-Skill fuer Android 11+ mit Root-Zugriff via Termux.

## Wichtig

- Alle Befehle brauchen **Root** (`su`)
- Manche Aktionen (Discoverable, Pairing) erfordern **UI-Bestaetigung auf dem Bildschirm**
- Scan oeffnet die Bluetooth-Einstellungen, die automatisch ein Discovery starten
- Fuer vollautomatische Steuerung ohne UI: nur `enable`, `disable`, `status`, `bonded`, `connected` moeglich

## Script

```bash
# Status abfragen
python3 skills/bluetooth/scripts/bluetooth.py status

# Bluetooth ein/ausschalten
python3 skills/bluetooth/scripts/bluetooth.py enable
python3 skills/bluetooth/scripts/bluetooth.py disable

# Nach Geraeten scannen (Standard: 12 Sek.)
python3 skills/bluetooth/scripts/bluetooth.py scan
python3 skills/bluetooth/scripts/bluetooth.py scan 20

# Gepaarte Geraete anzeigen
python3 skills/bluetooth/scripts/bluetooth.py bonded

# Aktuell verbundene Geraete
python3 skills/bluetooth/scripts/bluetooth.py connected

# Geraete-Info (Details zu einem bestimmten Geraet)
python3 skills/bluetooth/scripts/bluetooth.py info AA:BB:CC:DD:EE:FF

# Pairing starten (erfordert UI-Bestaetigung)
python3 skills/bluetooth/scripts/bluetooth.py pair AA:BB:CC:DD:EE:FF

# Pairing entfernen
python3 skills/bluetooth/scripts/bluetooth.py unpair AA:BB:CC:DD:EE:FF

# Mit Bluetooth-Lautsprecher/Kopfhoerer verbinden
python3 skills/bluetooth/scripts/bluetooth.py connect AA:BB:CC:DD:EE:FF
python3 skills/bluetooth/scripts/bluetooth.py connect AA:BB:CC:DD:EE:FF a2dp

# Geraet trennen
python3 skills/bluetooth/scripts/bluetooth.py disconnect AA:BB:CC:DD:EE:FF

# Datei per Bluetooth senden (OPP)
python3 skills/bluetooth/scripts/bluetooth.py send /pfad/zur/datei.pdf

# Sichtbar machen (erfordert UI-Bestaetigung)
python3 skills/bluetooth/scripts/bluetooth.py discoverable
python3 skills/bluetooth/scripts/bluetooth.py discoverable 300

# Audio-Routing anzeigen
python3 skills/bluetooth/scripts/bluetooth.py audio

# Geraetename aendern
python3 skills/bluetooth/scripts/bluetooth.py set-name "MeinTablet"
```

## Befehle

| Befehl        | Beschreibung                                 | UI noetig? |
|---------------|----------------------------------------------|------------|
| status        | Adapterstatus (Name, Adresse, Modus)         | Nein       |
| enable        | Bluetooth einschalten                        | Nein       |
| disable       | Bluetooth ausschalten                        | Nein       |
| scan [sek]    | Geraete in der Naehe suchen                  | Nein*      |
| bonded        | Gepaarte Geraete auflisten                   | Nein       |
| connected     | Verbundene Geraete auflisten                 | Nein       |
| info <mac>    | Detailinfos zu einem Geraet                  | Nein       |
| pair <mac>    | Pairing starten                              | **Ja**     |
| unpair <mac>  | Pairing entfernen                            | **Ja**     |
| connect <mac> | Mit gepaartem Geraet verbinden               | **Ja**     |
| disconnect    | Verbindung trennen                           | **Ja**     |
| send <pfad>   | Datei per Bluetooth senden (OPP)             | **Ja**     |
| discoverable  | Sichtbar machen                              | **Ja**     |
| audio         | Audio-Routing-Infos                          | Nein       |
| set-name      | Bluetooth-Name aendern                       | Nein       |

*Scan oeffnet BT-Einstellungen im Hintergrund, braucht aber keine User-Interaktion.

## Ausgabe

Alle Befehle geben **JSON** zurueck. Beispiel:

```json
{
  "enabled": true,
  "name": "Galaxy Tab A",
  "address": "58:C5:CB:E8:98:BE",
  "scan_mode": "connectable",
  "discovering": false,
  "connection_state": "DISCONNECTED",
  "profiles": ["A2dpService", "HeadsetService", "HidHostService"]
}
```

## Workflow: Datei an Handy senden

1. `bluetooth.py status` → pruefen ob BT an
2. `bluetooth.py enable` → falls aus, einschalten
3. `bluetooth.py bonded` → pruefen ob Zielgeraet gepaart
4. Falls nicht gepaart: `bluetooth.py scan` → Geraet finden,
   dann `bluetooth.py pair <mac>` → User bestaetigt PIN
5. `bluetooth.py send /pfad/zur/datei.pdf` → User waehlt Zielgeraet

## Workflow: Bluetooth-Lautsprecher verbinden

1. `bluetooth.py status` → pruefen ob BT an
2. `bluetooth.py enable` → falls noetig
3. `bluetooth.py bonded` → Lautsprecher suchen
4. Falls nicht gepaart: `bluetooth.py scan` → Lautsprecher suchen und dann pairen
5. `bluetooth.py connect <mac>` → Audio-Verbindung herstellen
6. `bluetooth.py audio` → Pruefen ob Audio geroutet wird

## Einschraenkungen

- Kein `bluetoothctl` oder `hcitool` verfuegbar (Android, kein BlueZ)
- Dateiempfang (OPP receive) kann nicht programmatisch gestartet werden —
  eingehende Dateien erscheinen in der Android-Benachrichtigungsleiste
- Discoverable erfordert User-Bestaetigung auf dem Bildschirm
- Pairing erfordert PIN-Bestaetigung auf beiden Geraeten

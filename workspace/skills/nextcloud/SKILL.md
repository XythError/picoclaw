---
name: nextcloud
description: "Nextcloud-Zugriff mit lokalem Spiegel (cloud/) + Kalender/Sharing via curl-Script."
---

# Nextcloud Skill

## Architektur: Lokaler Spiegel + automatischer Sync

Dein Nextcloud-Speicher ist lokal gespiegelt unter:
```
~/.picoclaw/workspace/cloud/
```

Ein rclone-bisync + vdirsyncer laeuft alle 5 Minuten automatisch per System-Cron.
Aenderungen die du lokal machst, landen automatisch auf Nextcloud (und umgekehrt).

**Dateien** werden per rclone bisync synchronisiert (cloud/ <-> nextcloud-files:).
**Kalender** werden per vdirsyncer synchronisiert (cloud/Calendar/ <-> CalDAV).

## WICHTIG -- So arbeitest du mit Dateien

### Dateien LESEN: Direkt lokal lesen!
```bash
exec({"command": "cat cloud/Rezepte/curry/recipe.json", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

### Dateien SCHREIBEN: Direkt lokal schreiben!
```bash
exec({"command": "mkdir -p cloud/Rezepte/neues-rezept && cat > cloud/Rezepte/neues-rezept/recipe.json << 'EOF'\n{...JSON...}\nEOF", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

### Dateien LOESCHEN: Direkt lokal loeschen!
```bash
exec({"command": "rm -rf cloud/Rezepte/altes-rezept", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

### Dateien AUFLISTEN: Direkt lokal!
```bash
exec({"command": "ls cloud/Rezepte/", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

### Sofort-Sync erzwingen (optional, nach wichtigen Aenderungen):
```bash
exec({"command": "bash nextcloud/nextcloud-sync.sh", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

## Verzeichnisstruktur in cloud/
- `cloud/Rezepte/` = PicoClaws eigener Ordner (hier schreiben!)
- `cloud/Shared/Rezepte/` = Geteilter Ordner von Elias (nur lesen)
- `cloud/Documents/` = Dokumente
- `cloud/Photos/` = Fotos
- `cloud/Calendar/personal/` = Kalender-Events (ICS-Dateien)
- `cloud/Calendar/contact_birthdays/` = Geburtstage

## Kalender

**WICHTIG: Kalender-Operationen ueber den haushalt-Skill!**
Fuer Termine erstellen/bearbeiten/loeschen/anzeigen:
→ `read_file` → `skills/haushalt/SKILL.md` laden, dann `haushalt.py` verwenden.

Kalender-Events liegen als .ics in `cloud/Calendar/personal/` (auto-sync via vdirsyncer).

## Freigaben (via nextcloud.sh)
```bash
exec({"command": "bash nextcloud/nextcloud.sh share Rezepte admin", "working_dir": "/data/data/com.termux/files/home/.picoclaw/workspace"})
```

## Verbindung (Referenz)
- Server: https://cloud.mytablab.de
- User: PicoClaw
- App-Passwort: 9gYYs-6fk48-7dAKz-69iMY-BGHkt
- Kalender: personal

## REGELN
- Dateien IMMER ueber cloud/ lesen/schreiben (NICHT ueber nextcloud.sh upload/download!)
- Kalender: IMMER ueber haushalt-Skill (haushalt.py cal-create/edit/delete)
- Kalender-Lesen: haushalt.py cal / haushalt.py heute
- Nur Sharing ueber nextcloud.sh share
- KEINE Subagents/spawn -- exec direkt!
- KEIN Python!
- Sync passiert automatisch alle 5 Min (Dateien + Kalender)
- Fuer sofort sichtbar auf Nextcloud: `bash nextcloud/nextcloud-sync.sh`

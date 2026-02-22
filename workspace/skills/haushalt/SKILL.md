---
name: haushalt
description: "Haushalts-Assistent + Kalender-Manager + TODOs. Wiederkehrende Aufgaben (Rotation + Check-off), CalDAV-CRUD und TODO-Verwaltung in einem Tool."
---

# Haushalt + Kalender + TODO Skill

Unified CLI fuer Haushaltsaufgaben, Kalender-Management und TODO-Listen.

## Quick Reference

```bash
# === TAGESANSICHT (Haushalt + Kalender + TODOs kombiniert) ===
python3 skills/haushalt/scripts/haushalt.py heute

# === HAUSHALT ===
python3 skills/haushalt/scripts/haushalt.py status
python3 skills/haushalt/scripts/haushalt.py erledigt "Spuelmaschine"
python3 skills/haushalt/scripts/haushalt.py next
python3 skills/haushalt/scripts/haushalt.py tasks
python3 skills/haushalt/scripts/haushalt.py add-task "Staubsaugen" "mi,sa" "Ganze Wohnung"
python3 skills/haushalt/scripts/haushalt.py remove-task "Staubsaugen"

# === TODOs ===
python3 skills/haushalt/scripts/haushalt.py todo-add "Arzttermin ausmachen" --bis 27.02.2026
python3 skills/haushalt/scripts/haushalt.py todo-add "Paket abholen"
python3 skills/haushalt/scripts/haushalt.py todo-done "Arzttermin"
python3 skills/haushalt/scripts/haushalt.py todo-list

# === KALENDER (CalDAV direkt, kein nextcloud.sh noetig) ===
python3 skills/haushalt/scripts/haushalt.py cal
python3 skills/haushalt/scripts/haushalt.py cal-create "Titel" 20260301T180000 20260301T190000 "Beschreibung"
python3 skills/haushalt/scripts/haushalt.py cal-edit picoclaw-123.ics --title "Neu" --start 20260301T190000
python3 skills/haushalt/scripts/haushalt.py cal-delete picoclaw-123.ics
python3 skills/haushalt/scripts/haushalt.py cal-show picoclaw-123.ics
python3 skills/haushalt/scripts/haushalt.py json
```

## WICHTIG: Kalender-Datumsberechnung

Alle cal-* Befehle geben zuerst das aktuelle Datum aus (z.B. "Heute: Freitag, 20.02.2026").
Nutze diese Info um relative Daten ("naechsten Sonntag", "uebermorgen") korrekt zu berechnen.
cal-create zeigt den Wochentag des erstellten Termins zur Kontrolle.

## User fragt "Was steht heute an?"

→ `python3 skills/haushalt/scripts/haushalt.py heute`

Zeigt kombiniert:
- Haushaltsaufgaben mit Check-off Status `[x]` / `[ ]`
- Kalender-Termine (max 10, naechste 14 Tage) mit `[dateiname.ics]`
- Offene TODOs mit optionalem Deadline

## TODO-System

User-Aufgaben die bis zur Erledigung bestehen bleiben.
Anders als Haushalt (taeglich wiederkehrend) sind TODOs einmalig.

### TODO erstellen
User sagt z.B. "Ich muss noch den Arzttermin ausmachen":
```bash
python3 skills/haushalt/scripts/haushalt.py todo-add "Arzttermin ausmachen" --bis 27.02.2026
```
- `--bis` ist optional (Deadline im Format DD.MM.YYYY oder YYYY-MM-DD)
- Ohne Deadline bleibt das TODO offen bis es erledigt wird

### TODO erledigen
User sagt z.B. "Arzttermin ist erledigt":
```bash
python3 skills/haushalt/scripts/haushalt.py todo-done "Arzttermin"
```
- Fuzzy-Matching (Teilstring reicht)
- Erledigte TODOs werden sofort entfernt

### TODO-Liste
```bash
python3 skills/haushalt/scripts/haushalt.py todo-list
```

## Aufgaben-System

### Wiederkehrende Aufgaben
- **Rotationen**: Zimmer (6, taeglich), Nebenraeume (3, Mo/Mi/Fr)
- **Feste Aufgaben**: Waesche (taeglich), Spuelmaschine (taeglich)
- Neue hinzufuegen: `add-task <name> <tage> [beschreibung]`
- Tage-Format: `mo,di,mi,do,fr,sa,so` oder `taeglich`

### Aufgabe abhaken
User sagt z.B. "Spuelmaschine erledigt":
```bash
python3 skills/haushalt/scripts/haushalt.py erledigt "Spuelmaschine"
```
- Fuzzy-Matching (Gross/Klein, Umlaute, Teilstring)
- "bad erledigt" → matcht Nebenraum wenn heute Bad dran ist
- Persistiert pro Tag, 7 Tage History

### Neue wiederkehrende Aufgabe
User sagt z.B. "Fuege mittwochs und samstags Staubsaugen hinzu":
```bash
python3 skills/haushalt/scripts/haushalt.py add-task "Staubsaugen" "mi,sa" "Ganze Wohnung"
```

## Kalender (CalDAV)

Termine liegen als ICS in `cloud/Calendar/personal/`.
CalDAV-Push ist direkt eingebaut — KEIN `nextcloud.sh` noetig!

Credentials werden aus Env/Secret-Datei geladen:
- `NEXTCLOUD_USER`, `NEXTCLOUD_PASS`, optional `NEXTCLOUD_URL`
- optional ueber `PICOCLAW_SECRETS_FILE` (Default: `~/.picoclaw/secrets.json`)

### Erstellen
```bash
python3 skills/haushalt/scripts/haushalt.py cal-create "Zahnarzt" 20260301T140000 20260301T150000 "Dr. Mueller"
```
Datum: `YYYYMMDDTHHMMSS` (Europe/Berlin automatisch)

### Bearbeiten
```bash
python3 skills/haushalt/scripts/haushalt.py cal-edit picoclaw-123.ics --title "Neuer Titel" --start 20260301T160000
```
Optionen: `--title`, `--start`, `--end`, `--desc` (nur geaenderte angeben)

### Loeschen
```bash
python3 skills/haushalt/scripts/haushalt.py cal-delete picoclaw-123.ics
```

### Output-Limit
- Max **10 Termine** oder **14 Tage** (was zuerst kommt)
- Immer **Dateiname in [brackets]** fuer Edit/Delete
- Alle ICS-Formate unterstuetzt (UTC, lokal, TZID)

## Cron

| Cron | Script | Funktion |
|------|--------|----------|
| `0 7 * * *` | morgen.py (deliver:true) | Morgen-Nachricht: Aufgaben + Termine + TODOs |
| `0 18 * * *` | abend.py (deliver:true) | Abend-Check: Offene TODOs abfragen |

## Dateien

| Datei | Inhalt |
|-------|--------|
| `scripts/haushalt.py` | Unified CLI (Haushalt + Kalender + TODOs) |
| `scripts/morgen.py` | Morgen-Cron (deliver:true) |
| `scripts/abend.py` | Abend-Cron (deliver:true) |
| `scripts/state.json` | Aufgaben-State + Check-off + TODOs |

---
name: dashboard
description: "Dashboard-Management auf Port 7000: Widgets dynamisch entwickeln, produktive Datenquellen synchronisieren, Interaktionen persistent verarbeiten und personalisiert aktuell halten."
---

````skill
# Dashboard Skill (Persönlichkeit + Produktivdaten)

## Mission
Dieses Skill macht das Dashboard zu einem **lebenden Teil von PicoClaws Persönlichkeit**:
- immer aktuell,
- individuell auf den User zugeschnitten,
- interaktiv,
- und strikt ohne Dummy-/Fake-Daten.

Dashboard URL: `http://192.168.2.50:7000/`

Script:
```bash
python3 skills/dashboard/scripts/dashboard.py <command>
```

---

## Guardrails (nicht verhandelbar)

1. **No Dummy Data:** Niemals Platzhalter, erfundene Werte oder Beispielinhalte als echte Information ausgeben.
2. **No Blind Writes:** Nie `dashboard/data.json` manuell editieren. Nur `update-widget`, `sync-data`, Template-Befehle und Skill-Skripte verwenden.
3. **Freshness First:** Vor user-sichtbaren Antworten bei datengetriebenen Widgets immer Datenquelle aktualisieren (`sync-data` oder skill-eigenen Fetch).
4. **Read-before-Write:** Bestehendes Widget lesen/erhalten; nur benötigte Felder ändern, niemals funktionierende Struktur überschreiben.
5. **Interaktiv = persistent:** Klicks/Aktionen müssen serverseitig gespeichert und nach Refresh weiterhin konsistent sein.
6. **Fail closed:** Wenn echte Datenquelle fehlschlägt, keine Fake-Ausgabe; stattdessen ehrlicher Status im Widget (z. B. „Quelle aktuell nicht erreichbar“).
7. **Personalisierung Pflicht:** Widget-Titel, Priorisierung und Inhalte auf aktuelle Nutzerziele/Alltag ausrichten.

---

## Skill-Load Ablauf (immer ausführen)

1. `python3 skills/dashboard/scripts/dashboard.py ensure-running`
2. `python3 skills/dashboard/scripts/dashboard.py health`
3. `python3 skills/dashboard/scripts/dashboard.py status`
4. `python3 skills/dashboard/scripts/dashboard.py list-widget-templates`
5. `python3 skills/dashboard/scripts/dashboard.py sync-data`

Wenn ein Check fehlschlägt: erst reparieren, dann weiterarbeiten.

---

## Kernbefehle

### Server
```bash
python3 skills/dashboard/scripts/dashboard.py ensure-running
python3 skills/dashboard/scripts/dashboard.py status
python3 skills/dashboard/scripts/dashboard.py restart
python3 skills/dashboard/scripts/dashboard.py health
```

### Widgets
```bash
python3 skills/dashboard/scripts/dashboard.py update-widget <id> '<json>'
python3 skills/dashboard/scripts/dashboard.py remove-widget <id>
python3 skills/dashboard/scripts/dashboard.py sync-data
```

### Templates
```bash
python3 skills/dashboard/scripts/dashboard.py export-widget-templates
python3 skills/dashboard/scripts/dashboard.py list-widget-templates
python3 skills/dashboard/scripts/dashboard.py save-widget-template <widget-id> [template-name]
python3 skills/dashboard/scripts/dashboard.py apply-widget-template <template-name> [new-widget-id]
```

### Watchdog
```bash
python3 skills/dashboard/scripts/watchdog.py ensure-running
python3 skills/dashboard/scripts/watchdog.py status
python3 skills/dashboard/scripts/watchdog.py install-cron
```

---

## Standard-Workflow für jeden neuen Widget-Wunsch

1. **Intent klären:** Was soll der User live sehen/steuern?
2. **Quelle festlegen:** Reale Datenquelle bestimmen (bestehendes Skill oder neues Skill).
3. **Widget wählen:** Bestehendes Widget erweitern oder Template anwenden.
4. **Minimal ändern:** Mit `update-widget` gezielt Felder setzen.
5. **Daten befüllen:** Reale Daten synchronisieren (`sync-data` oder skill-spezifischer Fetch).
6. **Interaktion testen:** Klick/Aktion -> Persistenz -> Reload prüfen.
7. **Template sichern:** Bei stabiler Struktur `save-widget-template`.

---

## Contract für neue (auch selbst entwickelte) Skills

Wenn PicoClaw auf User-Wunsch neue Skills erstellt, müssen Dashboard-Integrationen diesem Vertrag folgen:

1. Skill liefert **maschinenlesbar** (JSON) aktuelle Daten.
2. Dashboard erhält einen klaren Mapper: Skill-JSON -> Widget-`data`.
3. Interaktionen nutzen eindeutige Actions (`<skill>-<action>`), mit serverseitiger Persistenz.
4. Fehlerpfad liefert Status-/Hinweistext, aber **keine erfundenen Daten**.
5. Nach Integration: `status`, `sync-data`, Interaktionsprobe dokumentiert erfolgreich.

Ziel: Neue Skills sollen ohne Sonderlogik-Wildwuchs als Widgets integrierbar sein.

---

## Produktive Datenquellen (Priorität)

- Haushalt, Tasks, TODOs, Kalender: `skills/haushalt/scripts/haushalt.py`
- Dashboard-Synchronisierung: `python3 skills/dashboard/scripts/dashboard.py sync-data`
- Weitere Skills: deren JSON-CLI/API (niemals freie Textausgaben parsen, wenn JSON verfügbar ist)

---

## Widget-Schema (Pflicht)

```json
{
  "id": "widget-id",
  "type": "widget-type",
  "title": "Titel",
  "size": "small|medium|large",
  "data": {}
}
```

---

## Anti-Patterns (verboten)

- Dummy-/Beispieldaten als echte Daten darstellen
- Widget ohne `data`
- Vollständiges Überschreiben bei kleiner Feldänderung
- Interaktive Oberfläche ohne Persistenz
- „Erfolg“ melden ohne `health`/`status`/Datenprobe

---

## Abschluss-Check vor User-Antwort

- [ ] Dashboard erreichbar (`health` OK)
- [ ] Widgets sichtbar und nicht leer
- [ ] Daten sind echt und aktuell synchronisiert
- [ ] Interaktionen bleiben nach Reload erhalten
- [ ] Änderungen sind user-spezifisch (keine generischen Platzhalter)

````

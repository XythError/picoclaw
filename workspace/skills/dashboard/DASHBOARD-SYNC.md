# 🦞 Dashboard Auto-Sync System

## Überblick

Das Dashboard synchronisiert sich jetzt **automatisch** mit deinem Kalender, TODOs und Haushalt-Plan. Keine manuellen Updates nötig — alles läuft im Hintergrund.

---

## ✨ Features

### 1. **Automatische Synchronisierung**
- **Intervall:** Alle 15 Minuten (via Cron)
- **Datenquellen:** Kalender, TODOs, Haushalt-Aufgaben
- **Widgets:** Werden automatisch aktualisiert

### 2. **Neue Widgets**

#### `calendar` Widget
```json
{
  "type": "calendar",
  "title": "Termine",
  "size": "large",
  "data": {
    "events": [
      {
        "date": "So 22.02.",
        "time": "14:00",
        "title": "Zahnarzt",
        "description": "Dr. Müller"
      }
    ]
  }
}
```

#### `todos` Widget
```json
{
  "type": "todos",
  "title": "Offene TODOs",
  "size": "medium",
  "data": {
    "items": [
      {
        "text": "Arzttermin ausmachen",
        "deadline": "27.02.2026"
      },
      {
        "text": "Paket abholen"
      }
    ]
  }
}
```

**Besseres Rendering:** Statt `[object Object]` wird jetzt:
- ✅ Vollständiger Text angezeigt
- 📅 Deadline angezeigt (falls vorhanden)
- ☐ Klickbar zum Abhaken
- ✨ Mit Animation entfernt

### 3. **Interaktive Funktionen**

#### Tasks abhaken (Haushalt)
```javascript
toggleTaskItem(elementId, taskText, isDone)
```
- Klick auf Task → wird abhakt/entfernt
- Visuelle Animation (✅ / ⬜)
- Benachrichtigung bestätigt Aktion

#### TODOs abhaken
```javascript
markTodoDone(elementId, todoText)
```
- Klick auf TODO → wird als erledigt markiert
- Entfernt sich mit Animation
- Benachrichtigung bestätigt Aktion

---

## 🔄 Synchronisierung

### Automatisch (Cron)
```bash
# Alle 15 Minuten
*/15 * * * * python3 skills/dashboard/scripts/dashboard.py sync-data
```

### Manuell
```bash
cd ~/.picoclaw/workspace
python3 skills/dashboard/scripts/dashboard.py sync-data
```

### Was wird synchronisiert?

1. **Kalender-Termine**
   - Quelle: `cloud/Calendar/personal/`
   - Zeigt nächste 10 Termine oder 14 Tage
   - Format: Datum, Uhrzeit, Titel, Beschreibung

2. **Haushalt-Aufgaben**
   - Quelle: `haushalt.py json`
   - Zeigt heutige Aufgaben
   - Status: erledigt/nicht erledigt
   - Klickbar zum Abhaken

3. **Offene TODOs**
   - Quelle: `haushalt.py todo-list`
   - Zeigt alle offenen TODOs
   - Mit Deadline (falls vorhanden)
   - Klickbar zum Abhaken

---

## 📊 Dashboard-Struktur

```
Dashboard (Port 7000)
├── Widgets
│   ├── clock (Uhrzeit)
│   ├── weather (Wetter)
│   ├── tasks (Haushalt heute)
│   ├── calendar (Termine) ← AUTO-SYNC
│   ├── todos (Offene TODOs) ← AUTO-SYNC
│   ├── status (System)
│   └── metric (Metriken)
├── Auto-Sync (alle 15 min)
│   ├── Kalender laden
│   ├── Haushalt laden
│   └── TODOs laden
└── Interaktionen
    ├── Task abhaken → haushalt.py erledigt
    └── TODO abhaken → haushalt.py todo-done
```

---

## 🚀 Verwendung

### Widgets erstellen
```bash
# Kalender-Widget
python3 dashboard.py update-widget calendar '{"type":"calendar","title":"Termine","size":"large","data":{"events":[]}}'

# TODO-Widget
python3 dashboard.py update-widget todos '{"type":"todos","title":"Offene TODOs","size":"medium","data":{"items":[]}}'

# Haushalt-Tasks (bereits vorhanden)
python3 dashboard.py update-widget tasks '{"type":"tasks","title":"Haushalt Heute","size":"large","data":{"items":[]}}'
```

### Widgets aktualisieren
```bash
# Manuell synchronisieren
python3 dashboard.py sync-data

# Status prüfen
python3 dashboard.py status
```

---

## 🎯 Workflow

### 1. User erstellt neuen Termin
```bash
python3 skills/haushalt/scripts/haushalt.py cal-create "Luca Geburtstag" 20260303T000000 20260303T235959 "Luca hat Geburtstag"
```

### 2. Cron-Job triggert Sync (nach max. 15 min)
```bash
python3 skills/dashboard/scripts/dashboard.py sync-data
```

### 3. Dashboard aktualisiert sich automatisch
- Browser lädt `data.json` regelmäßig
- `calendar` Widget zeigt neuen Termin
- Keine manuelle Aktion nötig ✨

### 4. User klickt auf Task/TODO
```javascript
// Browser sendet Action
POST /api/action
{
  "action": "haushalt-task-done",
  "task_text": "Spülmaschine"
}
```

### 5. Dashboard aktualisiert sofort
- Task wird abhakt
- Benachrichtigung zeigt Erfolg
- Widget wird aktualisiert

---

## 🔧 Technische Details

### Dashboard-Script (`dashboard.py`)

#### Neue Funktion: `cmd_sync_data()`
```python
def cmd_sync_data():
    """Synchronisiere Dashboard mit Kalender, TODOs und Haushalt"""
    # 1. Kalender-Termine laden (haushalt.py cal)
    # 2. Haushalt-Aufgaben laden (haushalt.py json)
    # 3. TODOs laden (haushalt.py todo-list)
    # 4. Widgets aktualisieren
    # 5. data.json speichern
```

#### Parser-Funktionen
- `parse_calendar_output()` - Konvertiert `haushalt.py cal` Output zu Events
- `parse_todo_output()` - Konvertiert `haushalt.py todo-list` Output zu Items

#### HTTP-Handler erweitert
- `_handle_action()` - Unterstützt `haushalt-task-done` und `haushalt-todo-done`
- `_update_tasks_widget()` - Aktualisiert Tasks-Widget nach Abhaken

### HTML-Template (`index.html`)

#### Neue Renderer
```javascript
// TODOs mit besserer Darstellung
todos: w => {
  // Zeigt Text, Deadline, Klick-Handler
}

// Verbesserte List-Darstellung
list: w => {
  // Unterstützt Strings und Objekte
}
```

#### Neue JavaScript-Funktionen
```javascript
// Task abhaken
toggleTaskItem(elementId, taskText, isDone)

// TODO abhaken
markTodoDone(elementId, todoText)
```

---

## 📋 Checkliste

- [x] `calendar` Widget erstellt
- [x] `todos` Widget erstellt
- [x] `sync-data` Befehl implementiert
- [x] Parser für Kalender, Haushalt, TODOs
- [x] Cron-Job (alle 15 min) eingerichtet
- [x] JavaScript-Funktionen für Task/TODO-Abhaken
- [x] Besseres TODO-Rendering (kein `[object Object]`)
- [x] Benachrichtigungen bei Aktionen
- [x] Animationen beim Abhaken

---

## 🎉 Ergebnis

**Vorher:**
- Manuelles Aktualisieren nötig
- `[object Object]` statt Inhalte
- Keine Interaktion möglich

**Nachher:**
- ✅ Automatische Synchronisierung (15 min)
- ✅ Schöne TODO/Kalender-Anzeige
- ✅ Klickbar zum Abhaken
- ✅ Animationen & Benachrichtigungen
- ✅ Immer synchron mit Kalender/TODOs/Haushalt

---

## 🚀 Nächste Ideen

- [ ] Echtzeit-Updates (WebSocket statt Polling)
- [ ] Kalender-Filter (nur heute, nächste Woche, etc.)
- [ ] TODO-Kategorien/Tags
- [ ] Haushalt-Statistiken (Aufgaben/Woche)
- [ ] Push-Benachrichtigungen bei fälligen TODOs
- [ ] Dashboard-Widget für Geburtstage/Events

---

**Version:** 1.0  
**Datum:** 2026-02-21  
**Status:** ✅ Production Ready

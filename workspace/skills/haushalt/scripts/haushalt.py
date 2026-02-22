#!/usr/bin/env python3
"""
Haushalts-Assistent + Kalender-Manager — Unified CLI.

Haushalt: Wiederkehrende Aufgaben mit Rotation + Check-off
Kalender: CalDAV CRUD (create/read/edit/delete) mit lokalem Spiegel
Kombiniert: "heute" zeigt Haushalt + Termine
"""

import json
import os
import sys
import subprocess
import re
import glob
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "state.json")
CAL_DIR = os.path.expanduser("~/.picoclaw/workspace/cloud/Calendar/personal")


def _load_secret(name, default=""):
    value = os.environ.get(name)
    if value:
        return value

    secret_file = os.environ.get("PICOCLAW_SECRETS_FILE", os.path.expanduser("~/.picoclaw/secrets.json"))
    try:
        if os.path.exists(secret_file):
            with open(secret_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            value = data.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        pass

    return default

# CalDAV
NC_URL = os.environ.get("NEXTCLOUD_URL", "https://cloud.mytablab.de")
NC_USER = _load_secret("NEXTCLOUD_USER", os.environ.get("NEXTCLOUD_USER", ""))
NC_PASS = _load_secret("NEXTCLOUD_PASS", os.environ.get("NEXTCLOUD_PASS", ""))
DAV_CAL = f"{NC_URL}/remote.php/dav/calendars/{NC_USER}/personal"

# Tage
TAGE_MAP = {"mo": 0, "di": 1, "mi": 2, "do": 3, "fr": 4, "sa": 5, "so": 6}
TAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
TAGE_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _date_context():
    """Aktuelles Datum mit Wochentag  hilft KI bei Datumsberechnung."""
    now = datetime.now()
    return f"Heute: {TAGE_LANG[now.weekday()]}, {now.strftime('%d.%m.%Y')} (KW {now.isocalendar()[1]})"


# =============================================================
# State Management
# =============================================================

def default_state():
    return {
        "rotations": {
            "zimmer": {
                "label": "Zimmer putzen",
                "items": ["Buero", "Wohnzimmer", "Kueche", "Esszimmer", "Kinderzimmer", "Schlafzimmer"],
                "index": 0,
                "days": [0, 1, 2, 3, 4, 5, 6]
            },
            "nebenraum": {
                "label": "Nebenraum",
                "items": ["Bad", "Klo", "Garderobe"],
                "index": 0,
                "days": [0, 2, 4]
            }
        },
        "fixed_tasks": [
            {"name": "Waesche", "desc": "waschen + aufraeumen", "days": [0, 1, 2, 3, 4, 5, 6]},
            {"name": "Spuelmaschine", "desc": "ausraeumen + einraeumen", "days": [0, 1, 2, 3, 4, 5, 6]}
        ],
        "completed": {},
        "last_advance": None
    }


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        if "zimmer_index" in state:
            state = _migrate_old_state(state)
        if "rotations" not in state:
            state = default_state()
        return state
    state = default_state()
    save_state(state)
    return state


def _migrate_old_state(old):
    """Migriere altes State-Format (zimmer_index/nebenraum_index)."""
    new = default_state()
    new["rotations"]["zimmer"]["index"] = old.get("zimmer_index", 0)
    new["rotations"]["nebenraum"]["index"] = old.get("nebenraum_index", 0)
    new["last_advance"] = old.get("last_advance_date")
    save_state(new)
    # termine.json entfernen (ersetzt durch CalDAV)
    termine_file = os.path.join(SCRIPT_DIR, "termine.json")
    if os.path.exists(termine_file):
        os.remove(termine_file)
    return new


def save_state(state):
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    state["completed"] = {
        k: v for k, v in state.get("completed", {}).items() if k >= cutoff
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# =============================================================
# Haushalt: Aufgaben-Logik
# =============================================================

def get_today_info():
    now = datetime.now()
    return {
        "date": now.strftime("%d.%m.%Y"),
        "weekday": now.weekday(),
        "weekday_name": TAGE_LANG[now.weekday()],
        "kw": now.isocalendar()[1],
        "iso_date": now.strftime("%Y-%m-%d"),
    }


def get_todays_tasks(state):
    """Heutige Aufgaben mit Erledigt-Status."""
    weekday = datetime.now().weekday()
    date_key = datetime.now().strftime("%Y-%m-%d")
    done = state.get("completed", {}).get(date_key, [])
    tasks = []

    for key, rot in state.get("rotations", {}).items():
        if weekday in rot.get("days", []):
            item = rot["items"][rot["index"] % len(rot["items"])]
            label = rot.get("label", key)
            tasks.append({
                "display": f"{label}: {item}",
                "match": label,
                "item": item,
                "done": label in done,
                "type": "rotation"
            })

    for ft in state.get("fixed_tasks", []):
        if weekday in ft.get("days", []):
            name = ft["name"]
            desc = ft.get("desc", "")
            display = f"{name}: {desc}" if desc else name
            tasks.append({
                "display": display,
                "match": name,
                "item": "",
                "done": name in done,
                "type": "fixed"
            })

    return tasks


def get_heutige_aufgaben(state):
    """Backward-compat fuer morgen.py."""
    tasks = get_todays_tasks(state)
    result = {
        "datum": datetime.now().strftime("%d.%m.%Y"),
        "wochentag": TAGE_LANG[datetime.now().weekday()],
        "kw": datetime.now().isocalendar()[1],
        "tasks": tasks,
    }
    return result


def advance(state):
    """Rotation 1x pro Tag weiterdrehen."""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_advance") == today:
        return state

    weekday = datetime.now().weekday()
    for key, rot in state.get("rotations", {}).items():
        if weekday in rot.get("days", []):
            rot["index"] = (rot["index"] + 1) % len(rot["items"])

    state["last_advance"] = today
    save_state(state)
    return state


def parse_days(days_str):
    """Parse 'mo,mi,fr' oder 'taeglich' in Liste von Wochentag-Ints."""
    s = days_str.lower().strip()
    if s in ("taeglich", "daily", "jeden tag", "alle"):
        return [0, 1, 2, 3, 4, 5, 6]

    days = set()
    for part in re.split(r'[,\s]+', s):
        part = part.strip().rstrip('s')  # "mittwochs" -> "mittwoch"
        for prefix, idx in [("mo", 0), ("di", 1), ("mi", 2),
                            ("do", 3), ("fr", 4), ("sa", 5), ("so", 6)]:
            if part.startswith(prefix):
                days.add(idx)
                break
    return sorted(days)


def days_label(days):
    if set(days) == {0, 1, 2, 3, 4, 5, 6}:
        return "taeglich"
    return ",".join(TAGE_KURZ[d] for d in days)


def _normalize(s):
    """Fuer Fuzzy-Matching: lowercase + Umlaute aufloesen."""
    return s.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


# =============================================================
# ICS Parsing
# =============================================================

def _parse_ics_dt(line):
    """Parse DTSTART/DTEND Zeile → datetime (Berliner Lokalzeit)."""
    m = re.search(r':(\d{8})(T(\d{4,6}))?(Z)?', line)
    if not m:
        return None
    date_s = m.group(1)
    time_s = m.group(3) or "000000"
    if len(time_s) == 4:
        time_s += "00"
    is_utc = m.group(4) == 'Z'

    dt = datetime.strptime(f"{date_s}{time_s}", "%Y%m%d%H%M%S")

    if is_utc:
        # UTC → Europe/Berlin (CET+1 / CEST+2)
        y = dt.year
        mar31 = datetime(y, 3, 31)
        dst_on = mar31 - timedelta(days=(mar31.weekday() + 1) % 7)
        dst_on = dst_on.replace(hour=1)
        oct31 = datetime(y, 10, 31)
        dst_off = oct31 - timedelta(days=(oct31.weekday() + 1) % 7)
        dst_off = dst_off.replace(hour=1)
        offset = 2 if dst_on <= dt < dst_off else 1
        dt += timedelta(hours=offset)

    return dt


def _has_time(line):
    """Pruefe ob DTSTART eine Uhrzeit enthaelt (nicht nur Datum)."""
    return bool(re.search(r'T\d{4,6}', line))


def parse_ics_file(filepath):
    """Parse ICS → Event-Dict oder None."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None

    if "BEGIN:VEVENT" not in content:
        return None

    filename = os.path.basename(filepath)
    uid_m = re.search(r"UID:([^\r\n]+)", content)
    sum_m = re.search(r"SUMMARY:([^\r\n]+)", content)
    desc_m = re.search(r"DESCRIPTION:([^\r\n]+)", content)
    start_m = re.search(r"DTSTART[^\r\n]*", content)
    end_m = re.search(r"DTEND[^\r\n]*", content)

    if not sum_m or not start_m:
        return None

    start_dt = _parse_ics_dt(start_m.group(0))
    end_dt = _parse_ics_dt(end_m.group(0)) if end_m else None
    allday = not _has_time(start_m.group(0))

    if not start_dt:
        return None

    return {
        "file": filename,
        "uid": uid_m.group(1).strip() if uid_m else filename.replace(".ics", ""),
        "summary": sum_m.group(1).strip(),
        "description": desc_m.group(1).strip() if desc_m else "",
        "start": start_dt,
        "end": end_dt,
        "allday": allday,
    }


def get_calendar_events(max_events=10, max_days=14, from_date=None):
    """Kommende Termine aus lokalen ICS-Dateien."""
    if not os.path.isdir(CAL_DIR):
        return []

    start = from_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=max_days)

    events = []
    for f in glob.glob(os.path.join(CAL_DIR, "*.ics")):
        ev = parse_ics_file(f)
        if ev and start <= ev["start"] < end:
            events.append(ev)

    events.sort(key=lambda x: x["start"])
    return events[:max_events]


# =============================================================
# CalDAV CRUD (via curl)
# =============================================================

def _curl(method, path, data=None):
    """CalDAV Request via curl."""
    if not NC_USER or not NC_PASS:
        return "ERR:missing_credentials"

    url = f"{DAV_CAL}/{path}" if path else f"{DAV_CAL}/"
    cmd = ["curl", "-s", "-k", "--max-time", "30",
           "-u", f"{NC_USER}:{NC_PASS}",
           "-X", method, "-o", "/dev/null", "-w", "%{http_code}"]
    if data:
        cmd += ["-H", "Content-Type: text/calendar; charset=utf-8", "-d", data]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        return r.stdout.strip()
    except Exception as e:
        return f"ERR:{e}"


def _build_ics(uid, title, dtstart, dtend, desc=""):
    """ICS-Inhalt generieren."""
    now = datetime.now(tz=None).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PicoClaw//NONSGML v1.0//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/Berlin:{dtstart}",
        f"DTEND;TZID=Europe/Berlin:{dtend}",
        f"SUMMARY:{title}",
    ]
    if desc:
        lines.append(f"DESCRIPTION:{desc}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\n".join(lines)


def cal_create(title, dtstart, dtend, desc=""):
    """Termin erstellen (CalDAV + lokal)."""
    print(_date_context())
    uid = f"picoclaw-{int(datetime.now().timestamp())}-{os.getpid()}"
    filename = f"{uid}.ics"
    ics = _build_ics(uid, title, dtstart, dtend, desc)

    code = _curl("PUT", filename, ics)

    if code in ("201", "204"):
        os.makedirs(CAL_DIR, exist_ok=True)
        with open(os.path.join(CAL_DIR, filename), "w") as f:
            f.write(ics)
        ev_dt = datetime.strptime(dtstart[:8], "%Y%m%d")
        ev_day = TAGE_LANG[ev_dt.weekday()]
        print(f"OK: Termin erstellt '{title}' ({ev_day} {ev_dt.strftime('%d.%m.%Y')} {dtstart[9:11]}:{dtstart[11:13]}) [{filename}]")
        return True
    else:
        print(f"FEHLER: CalDAV HTTP {code}")
        return False


def cal_edit(uid_or_file, title=None, dtstart=None, dtend=None, desc=None):
    """Termin bearbeiten (CalDAV + lokal)."""
    print(_date_context())
    filename, local_path, ev = _find_event(uid_or_file)
    if not ev:
        return False

    new_title = title or ev["summary"]
    new_desc = desc if desc is not None else ev["description"]
    new_start = dtstart or ev["start"].strftime("%Y%m%dT%H%M%S")
    if dtend:
        new_end = dtend
    elif dtstart and ev["end"] and ev["start"]:
        # Shift end by same delta as start changed
        duration = ev["end"] - ev["start"]
        new_start_dt = datetime.strptime(dtstart, "%Y%m%dT%H%M%S")
        new_end = (new_start_dt + duration).strftime("%Y%m%dT%H%M%S")
    elif ev["end"]:
        new_end = ev["end"].strftime("%Y%m%dT%H%M%S")
    else:
        fallback = ev["start"] + timedelta(hours=1)
        new_end = fallback.strftime("%Y%m%dT%H%M%S")

    ics = _build_ics(ev["uid"], new_title, new_start, new_end, new_desc)
    code = _curl("PUT", filename, ics)

    if code in ("201", "204"):
        with open(local_path, "w") as f:
            f.write(ics)
        print(f"OK: Termin aktualisiert '{new_title}' [{filename}]")
        return True
    else:
        print(f"FEHLER: CalDAV HTTP {code}")
        return False


def cal_delete(uid_or_file):
    """Termin loeschen (CalDAV + lokal)."""
    print(_date_context())
    filename, local_path, ev = _find_event(uid_or_file)
    if not ev:
        # Trotzdem versuchen remote zu loeschen
        filename = uid_or_file if uid_or_file.endswith(".ics") else f"{uid_or_file}.ics"
        local_path = os.path.join(CAL_DIR, filename)

    code = _curl("DELETE", filename)

    if code in ("204", "404"):
        if os.path.exists(local_path):
            os.remove(local_path)
        print(f"OK: Termin geloescht [{filename}]")
        return True
    else:
        print(f"FEHLER: CalDAV HTTP {code}")
        return False


def _find_event(uid_or_file):
    """Event per UID oder Dateiname finden → (filename, local_path, event)."""
    filename = uid_or_file if uid_or_file.endswith(".ics") else f"{uid_or_file}.ics"
    local_path = os.path.join(CAL_DIR, filename)

    if os.path.exists(local_path):
        ev = parse_ics_file(local_path)
        if ev:
            return filename, local_path, ev

    # Suche per UID
    for f in glob.glob(os.path.join(CAL_DIR, "*.ics")):
        ev = parse_ics_file(f)
        if ev and (ev["uid"] == uid_or_file or ev["file"] == uid_or_file):
            return ev["file"], f, ev

    print(f"FEHLER: Termin nicht gefunden: {uid_or_file}")
    return filename, local_path, None


# =============================================================
# CLI: Kombinierte Ansicht
# =============================================================

def cmd_heute():
    """Haushalt + Kalender kombiniert."""
    state = load_state()
    today = datetime.now()
    info = get_today_info()

    print(f"📅 {info['weekday_name']}, {info['date']} (KW {info['kw']})")

    tasks = get_todays_tasks(state)
    if tasks:
        print("\n🧹 Haushalt:")
        for t in tasks:
            mark = "x" if t["done"] else " "
            print(f"  [{mark}] {t['display']}")

    events = get_calendar_events(max_events=10, max_days=14)
    if events:
        print(f"\n📅 Termine (max 10, 14 Tage):")
        for ev in events:
            _print_event(ev)

    # TODOs
    todos = get_todos(state)
    if todos:
        print(f"\n\U0001f4cb TODOs ({len(todos)}):")
        for t in todos:
            dl = f" (bis {t['deadline']})" if "deadline" in t else ""
            print(f"  \u25fb {t['text']}{dl}")

    if not tasks and not events and not todos:
        print("\nKeine Aufgaben, Termine oder TODOs.")


def cmd_status():
    """Nur Haushalt-Status."""
    state = load_state()
    info = get_today_info()
    tasks = get_todays_tasks(state)

    print(f"🧹 Haushalt {info['weekday_name']} {info['date']}:")
    for t in tasks:
        mark = "x" if t["done"] else " "
        print(f"  [{mark}] {t['display']}")

    print()
    for key, rot in state.get("rotations", {}).items():
        i = rot["index"]
        n = len(rot["items"])
        print(f"  Rotation {rot['label']}: {i + 1}/{n} ({rot['items'][i]})")


def cmd_erledigt(task_name):
    """Aufgabe als erledigt markieren."""
    state = load_state()
    date_key = datetime.now().strftime("%Y-%m-%d")

    if date_key not in state.get("completed", {}):
        state.setdefault("completed", {})[date_key] = []

    tasks = get_todays_tasks(state)
    search = _normalize(task_name)
    matched = None

    for t in tasks:
        dn = _normalize(t["display"])
        mn = _normalize(t["match"])
        it = _normalize(t.get("item", ""))
        if search in dn or search in mn or search in it or mn.startswith(search):
            matched = t
            break

    if not matched:
        print(f"FEHLER: '{task_name}' heute nicht gefunden.")
        print("Heutige Aufgaben:")
        for t in tasks:
            print(f"  - {t['display']}")
        return

    key = matched["match"]
    if key not in state["completed"][date_key]:
        state["completed"][date_key].append(key)

    save_state(state)
    print(f"✅ Erledigt: {matched['display']}")


def cmd_next():
    """Rotation weiterdrehen."""
    state = load_state()
    today = datetime.now().strftime("%Y-%m-%d")

    if state.get("last_advance") == today:
        print("ℹ️  Heute bereits rotiert.")
        return

    weekday = datetime.now().weekday()
    msgs = []
    for key, rot in state.get("rotations", {}).items():
        if weekday in rot.get("days", []):
            old = rot["items"][rot["index"]]
            rot["index"] = (rot["index"] + 1) % len(rot["items"])
            msgs.append(f"  {rot['label']}: {old} → {rot['items'][rot['index']]}")

    state["last_advance"] = today
    save_state(state)

    if msgs:
        print("✅ Rotation:")
        for m in msgs:
            print(m)
    else:
        print("✅ Rotiert (keine Rotation heute faellig).")


def cmd_add_task(name, days_str, desc=""):
    """Wiederkehrende Aufgabe hinzufuegen/aktualisieren."""
    state = load_state()
    days = parse_days(days_str)

    if not days:
        print(f"FEHLER: Ungueltige Tage: {days_str}")
        print("Format: mo,di,mi,do,fr,sa,so oder 'taeglich'")
        return

    for ft in state.get("fixed_tasks", []):
        if ft["name"].lower() == name.lower():
            ft["days"] = days
            if desc:
                ft["desc"] = desc
            save_state(state)
            print(f"✅ Aktualisiert: {name} ({days_label(days)})")
            return

    state.setdefault("fixed_tasks", []).append({
        "name": name, "desc": desc, "days": days
    })
    save_state(state)
    print(f"✅ Hinzugefuegt: {name} ({days_label(days)})")


def cmd_remove_task(name):
    """Wiederkehrende Aufgabe entfernen."""
    state = load_state()
    search = name.lower()

    for i, ft in enumerate(state.get("fixed_tasks", [])):
        if ft["name"].lower() == search or search in ft["name"].lower():
            removed = state["fixed_tasks"].pop(i)
            save_state(state)
            print(f"✅ Entfernt: {removed['name']}")
            return

    print(f"FEHLER: Aufgabe '{name}' nicht gefunden.")


def cmd_tasks():
    """Alle konfigurierten Aufgaben anzeigen."""
    state = load_state()

    print("📋 Wiederkehrende Aufgaben:\n")
    for key, rot in state.get("rotations", {}).items():
        print(f"  🔄 {rot['label']} ({days_label(rot['days'])})")
        print(f"     {' → '.join(rot['items'])}")
        print(f"     Aktuell: {rot['items'][rot['index']]}")

    for ft in state.get("fixed_tasks", []):
        desc = f" — {ft['desc']}" if ft.get("desc") else ""
        print(f"  📌 {ft['name']} ({days_label(ft['days'])}){desc}")




# =============================================================
# TODO System
# =============================================================

def get_todos(state):
    """Offene TODOs aus State laden."""
    return state.get("todos", [])


def cmd_todo_add(text, deadline=None):
    """TODO hinzufuegen."""
    state = load_state()
    todo = {
        "text": text,
        "created": datetime.now().strftime("%Y-%m-%d"),
    }
    if deadline:
        parsed = _parse_date(deadline)
        if parsed:
            todo["deadline"] = parsed.strftime("%Y-%m-%d")
        else:
            print(f"FEHLER: Ungueltiges Datum: {deadline}")
            return
    state.setdefault("todos", []).append(todo)
    save_state(state)
    dl = f" (bis {todo['deadline']})" if "deadline" in todo else ""
    print(f"\u2705 TODO erstellt: {text}{dl}")


def cmd_todo_done(search):
    """TODO als erledigt markieren (entfernen)."""
    state = load_state()
    todos = state.get("todos", [])
    if not todos:
        print("Keine offenen TODOs.")
        return

    search_n = _normalize(search)
    matched = None
    matched_idx = None

    for i, t in enumerate(todos):
        if search_n in _normalize(t["text"]):
            matched = t
            matched_idx = i
            break

    if matched is None:
        print(f"FEHLER: TODO '{search}' nicht gefunden.")
        print("Offene TODOs:")
        for t in todos:
            print(f"  - {t['text']}")
        return

    todos.pop(matched_idx)
    state["todos"] = todos
    save_state(state)
    print(f"\u2705 TODO erledigt: {matched['text']}")


def cmd_todo_list():
    """Alle offenen TODOs anzeigen."""
    print(_date_context())
    state = load_state()
    todos = get_todos(state)
    if not todos:
        print("Keine offenen TODOs. \U0001f389")
        return
    print(f"\U0001f4cb Offene TODOs ({len(todos)}):")
    for i, t in enumerate(todos, 1):
        dl = f" (bis {t['deadline']})" if "deadline" in t else ""
        age = (datetime.now() - datetime.strptime(t["created"], "%Y-%m-%d")).days
        print(f"  {i}. {t['text']}{dl}  [{age}d]")


# =============================================================
# CLI: Kalender
# =============================================================

def cmd_cal(date_str=None):
    """Termine anzeigen (max 10, 14 Tage)."""
    print(_date_context())
    from_date = None
    if date_str:
        from_date = _parse_date(date_str)
        if not from_date:
            print(f"FEHLER: Ungueltiges Datum: {date_str}")
            return

    events = get_calendar_events(max_events=10, max_days=14, from_date=from_date)
    start = from_date or datetime.now()

    if events:
        print(f"📅 Termine (max 10, 14 Tage ab {start.strftime('%d.%m.%Y')}):")
        for ev in events:
            _print_event(ev)
    else:
        print("ℹ️  Keine Termine in den naechsten 14 Tagen.")


def cmd_cal_show(uid_or_file):
    """Einzeltermin-Details."""
    print(_date_context())
    _, _, ev = _find_event(uid_or_file)
    if not ev:
        return

    print(f"📅 {ev['summary']}")
    print(f"   Datei: {ev['file']}")
    print(f"   UID: {ev['uid']}")
    if ev["allday"]:
        print(f"   Datum: {ev['start'].strftime('%d.%m.%Y')} (ganztaegig)")
    else:
        print(f"   Start: {ev['start'].strftime('%d.%m.%Y %H:%M')}")
        if ev["end"]:
            print(f"   Ende:  {ev['end'].strftime('%d.%m.%Y %H:%M')}")
    if ev["description"]:
        print(f"   Beschreibung: {ev['description']}")


def cmd_json():
    """Alles als JSON (fuer Automatisierung)."""
    state = load_state()
    tasks = get_todays_tasks(state)
    events = get_calendar_events(max_events=10, max_days=14)

    todos = get_todos(state)
    out = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "weekday": TAGE_LANG[datetime.now().weekday()],
        "kw": datetime.now().isocalendar()[1],
        "tasks": [{"display": t["display"], "done": t["done"]} for t in tasks],
        "todos": todos,
        "events": [{
            "file": e["file"], "uid": e["uid"], "summary": e["summary"],
            "start": e["start"].isoformat(),
            "end": e["end"].isoformat() if e["end"] else None,
        } for e in events]
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


# =============================================================
# Hilfsfunktionen
# =============================================================

def _print_event(ev):
    """Einzelne Termin-Zeile ausgeben."""
    d = ev["start"].strftime("%d.%m.")
    day = TAGE_KURZ[ev["start"].weekday()]
    if ev["allday"]:
        print(f"  {day} {d} ganztaegig {ev['summary']} [{ev['file']}]")
    else:
        t = ev["start"].strftime("%H:%M")
        end = f"-{ev['end'].strftime('%H:%M')}" if ev["end"] else ""
        print(f"  {day} {d} {t}{end} {ev['summary']} [{ev['file']}]")


def _parse_date(s):
    """Datum-String parsen (DD.MM.YYYY, YYYY-MM-DD, YYYYMMDD)."""
    try:
        if "." in s:
            p = s.split(".")
            return datetime(int(p[2]), int(p[1]), int(p[0]))
        elif "-" in s:
            p = s.split("-")
            return datetime(int(p[0]), int(p[1]), int(p[2]))
        else:
            return datetime.strptime(s, "%Y%m%d")
    except (IndexError, ValueError):
        return None


# =============================================================
# Main CLI
# =============================================================

def main():
    if len(sys.argv) < 2:
        cmd_heute()
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "heute":
        cmd_heute()
    elif cmd == "status":
        cmd_status()
    elif cmd == "erledigt":
        if not args:
            print("Usage: haushalt.py erledigt <aufgabe>")
        else:
            cmd_erledigt(" ".join(args))
    elif cmd == "next":
        cmd_next()
    elif cmd == "add-task":
        if len(args) < 2:
            print("Usage: haushalt.py add-task <name> <tage> [beschreibung]")
            print("  Tage: mo,di,mi,fr,sa,so oder 'taeglich'")
        else:
            cmd_add_task(args[0], args[1], " ".join(args[2:]) if len(args) > 2 else "")
    elif cmd == "remove-task":
        if not args:
            print("Usage: haushalt.py remove-task <name>")
        else:
            cmd_remove_task(args[0])
    elif cmd == "tasks":
        cmd_tasks()
    elif cmd == "cal":
        cmd_cal(args[0] if args else None)
    elif cmd == "cal-create":
        if len(args) < 3:
            print("Usage: haushalt.py cal-create <titel> <start> <end> [beschreibung]")
            print("  Datum: YYYYMMDDTHHMMSS (z.B. 20260301T180000)")
        else:
            cal_create(args[0], args[1], args[2], " ".join(args[3:]) if len(args) > 3 else "")
    elif cmd == "cal-edit":
        if len(args) < 2:
            print("Usage: haushalt.py cal-edit <uid/datei> [--title X] [--start YYYYMMDDTHHMMSS] [--end YYYYMMDDTHHMMSS] [--desc X]")
        else:
            uid = args[0]
            t = s = e = d = None
            i = 1
            while i < len(args):
                if args[i] == "--title" and i + 1 < len(args):
                    # Collect all words until next --flag
                    parts = []
                    i += 1
                    while i < len(args) and not args[i].startswith("--"):
                        parts.append(args[i]); i += 1
                    t = " ".join(parts)
                elif args[i] == "--start" and i + 1 < len(args):
                    s = args[i + 1]; i += 2
                elif args[i] == "--end" and i + 1 < len(args):
                    e = args[i + 1]; i += 2
                elif args[i] == "--desc" and i + 1 < len(args):
                    parts = []
                    i += 1
                    while i < len(args) and not args[i].startswith("--"):
                        parts.append(args[i]); i += 1
                    d = " ".join(parts)
                else:
                    i += 1
            cal_edit(uid, title=t, dtstart=s, dtend=e, desc=d)
    elif cmd == "cal-delete":
        if not args:
            print("Usage: haushalt.py cal-delete <uid/datei>")
        else:
            cal_delete(args[0])
    elif cmd == "cal-show":
        if not args:
            print("Usage: haushalt.py cal-show <uid/datei>")
        else:
            cmd_cal_show(args[0])
    elif cmd == "todo-add":
        if not args:
            print("Usage: haushalt.py todo-add <text> [--bis DATUM]")
            print("  Datum: DD.MM.YYYY oder YYYY-MM-DD")
        else:
            # Parse --bis flag
            deadline = None
            text_parts = []
            i = 0
            while i < len(args):
                if args[i] == "--bis" and i + 1 < len(args):
                    deadline = args[i + 1]
                    i += 2
                else:
                    text_parts.append(args[i])
                    i += 1
            cmd_todo_add(" ".join(text_parts), deadline)
    elif cmd == "todo-done":
        if not args:
            print("Usage: haushalt.py todo-done <suchtext>")
        else:
            cmd_todo_done(" ".join(args))
    elif cmd == "todo-list":
        cmd_todo_list()
    elif cmd == "json":
        cmd_json()
    else:
        print(f"Unbekannt: {cmd}")
        print("Befehle: heute status erledigt next add-task remove-task tasks todo-add todo-done todo-list cal cal-create cal-edit cal-delete cal-show json")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PicoClaw Dashboard Manager 🦞

Web-Dashboard mit Widgets, Buttons und Benachrichtigungen.
Stdlib only — keine externen Dependencies.

Befehle:
  init / serve / ensure-running / status
  update-widget <id> '<json>' / remove-widget <id>
  add-button <id> <label> <action> [icon] [desc] / remove-button <id>
  set-status <online|offline|busy> / set-message '<text>'
  notify '<text>' [level] / pending / clear-pending [id]
"""

import json
import os
import sys
import time
import datetime
import shutil
import signal
import subprocess
import re
import shlex
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# === Configuration ===
HOME = os.path.expanduser("~")
WORKSPACE = os.path.join(HOME, ".picoclaw", "workspace")
DASHBOARD_DIR = os.path.join(WORKSPACE, "dashboard")
DATA_FILE = os.path.join(DASHBOARD_DIR, "data.json")
PENDING_FILE = os.path.join(DASHBOARD_DIR, "pending.json")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(SKILL_DIR, "templates")
PORT = 7000
PID_FILE = os.path.join(DASHBOARD_DIR, "server.pid")
WIDGET_TEMPLATE_DIR = os.path.join(SKILL_DIR, "widget_templates")
EXEC_ENABLED = os.environ.get("DASHBOARD_EXEC_ENABLED", "0") == "1"
EXEC_ALLOWLIST = {
    cmd.strip() for cmd in os.environ.get(
        "DASHBOARD_EXEC_ALLOWLIST",
        "echo,date,uptime,whoami,free,df"
    ).split(",") if cmd.strip()
}


WIDGET_SIZE_DEFAULTS = {
    "clock": "small",
    "metric": "small",
    "weather": "medium",
    "calendar": "medium",
    "status": "medium",
    "text": "medium",
    "list": "medium",
    "todos": "medium",
    "image": "medium",
    "tasks": "large",
    "terminal": "large",
    "recipe": "large",
    "video": "large",
    "game": "large",
}


def default_widget_data(widget_type):
    defaults = {
        "clock": {},
        "weather": {
            "temp": "--",
            "condition": "--",
            "humidity": "--",
            "wind": "--",
            "forecast": "",
            "location": "",
        },
        "tasks": {"items": []},
        "calendar": {"events": []},
        "status": {"items": []},
        "metric": {"value": "--", "unit": "", "trend": ""},
        "text": {"content": "Noch keine Inhalte."},
        "list": {"items": []},
        "todos": {"items": []},
        "terminal": {"output": "Bereit für Befehle..."},
        "recipe": {
            "name": "Rezept",
            "description": "",
            "ingredients": [],
            "steps": [],
        },
        "game": {"title": "Spiel", "description": ""},
        "image": {"url": "", "alt": "", "caption": ""},
        "video": {"url": "", "poster": "", "caption": ""},
    }
    base = defaults.get(widget_type, {})
    return json.loads(json.dumps(base))


def widget_title_from_id(widget_id):
    return re.sub(r"[_-]+", " ", str(widget_id)).strip().title() or "Widget"


def normalize_widget_input(widget_id, input_data, existing_widget=None):
    if not isinstance(input_data, dict):
        input_data = {}

    existing_widget = existing_widget or {}
    has_widget_shape = "type" in input_data or "data" in input_data

    if has_widget_shape:
        widget = dict(input_data)
    else:
        widget = {"data": dict(input_data)}

    widget_type = str(widget.get("type") or existing_widget.get("type") or "text")
    widget["type"] = widget_type

    existing_data = existing_widget.get("data") if isinstance(existing_widget.get("data"), dict) else {}
    explicit_data = "data" in widget
    provided_data = widget.get("data") if isinstance(widget.get("data"), dict) else {}

    defaults = default_widget_data(widget_type)
    if explicit_data:
        merged = dict(defaults)
        if not provided_data and existing_data:
            merged.update(existing_data)
        else:
            merged.update(provided_data)
    else:
        merged = dict(defaults)
        merged.update(existing_data)

    widget["id"] = widget_id
    widget["data"] = merged
    widget["title"] = widget.get("title") or existing_widget.get("title") or widget_title_from_id(widget_id)
    widget["size"] = widget.get("size") or existing_widget.get("size") or WIDGET_SIZE_DEFAULTS.get(widget_type, "medium")

    if "position" not in widget:
        if "position" in existing_widget:
            widget["position"] = existing_widget.get("position")

    return widget


def ensure_widget_template_dir():
    os.makedirs(WIDGET_TEMPLATE_DIR, exist_ok=True)


def sanitize_template_name(name):
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", (name or "").strip())
    return safe.strip("-._") or "template"


def save_widget_template_file(template_name, widget):
    ensure_widget_template_dir()
    template_name = sanitize_template_name(template_name)
    target = os.path.join(WIDGET_TEMPLATE_DIR, f"{template_name}.json")
    save_json(target, widget)
    return target


def load_widget_template_file(template_name):
    template_name = sanitize_template_name(template_name)
    path = os.path.join(WIDGET_TEMPLATE_DIR, f"{template_name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def cmd_save_widget_template(widget_id, template_name=None):
    data = load_data()
    widget = next((w for w in data.get("widgets", []) if w.get("id") == widget_id), None)
    if not widget:
        print(f"❌ Widget '{widget_id}' nicht gefunden")
        sys.exit(1)

    template = template_name or widget_id
    path = save_widget_template_file(template, widget)
    print(f"✅ Widget-Template gespeichert: {path}")


def cmd_export_widget_templates():
    data = load_data()
    widgets = data.get("widgets", [])
    if not widgets:
        print("⚠️ Keine Widgets zum Exportieren vorhanden")
        return

    ensure_widget_template_dir()
    exported = []
    for widget in widgets:
        wid = widget.get("id") or f"widget-{len(exported)+1}"
        path = save_widget_template_file(wid, widget)
        exported.append({"id": wid, "path": path})

    manifest = {
        "exported_at": now_iso(),
        "count": len(exported),
        "templates": exported,
    }
    save_json(os.path.join(WIDGET_TEMPLATE_DIR, "_manifest.json"), manifest)
    print(f"✅ {len(exported)} Widget-Templates exportiert nach {WIDGET_TEMPLATE_DIR}")


def cmd_list_widget_templates():
    ensure_widget_template_dir()
    files = sorted(
        f for f in os.listdir(WIDGET_TEMPLATE_DIR)
        if f.endswith(".json") and not f.startswith("_")
    )
    if not files:
        print("⚠️ Keine Widget-Templates vorhanden")
        return

    print(f"📦 Widget-Templates ({len(files)}):")
    for filename in files:
        print(f"  - {filename[:-5]}")


def cmd_apply_widget_template(template_name, widget_id=None):
    try:
        template, path = load_widget_template_file(template_name)
    except FileNotFoundError:
        print(f"❌ Template nicht gefunden: {template_name}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Ungültiges Template JSON: {e}")
        sys.exit(1)

    target_id = widget_id or template.get("id") or sanitize_template_name(template_name)
    cmd_update_widget(target_id, json.dumps(template, ensure_ascii=False))
    print(f"✅ Template angewendet: {path} -> Widget '{target_id}'")


# === Data Management ===

def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def load_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}

def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_data():
    return load_json(DATA_FILE, default_data())

def save_data(data):
    data["meta"]["updated"] = now_iso()
    save_json(DATA_FILE, data)

def load_pending():
    return load_json(PENDING_FILE, [])

def save_pending(pending):
    save_json(PENDING_FILE, pending)

def default_data():
    return {
        "meta": {
            "title": "PicoClaw Dashboard 🦞",
            "updated": now_iso(),
            "agent_status": "online",
            "agent_message": "",
            "theme": "dark",
            "refresh_interval": 15
        },
        "widgets": [
            {
                "id": "clock",
                "type": "clock",
                "title": "Uhrzeit",
                "data": {},
                "position": 0,
                "size": "small"
            }
        ],
        "buttons": [],
        "notifications": []
    }


# === Commands ===

def cmd_init():
    os.makedirs(DASHBOARD_DIR, exist_ok=True)

    src = os.path.join(TEMPLATE_DIR, "index.html")
    dst = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✅ Template kopiert: {dst}")
    else:
        print(f"❌ Template nicht gefunden: {src}")
        return

    if not os.path.exists(DATA_FILE):
        save_data(default_data())
        print(f"✅ data.json erstellt")

    if not os.path.exists(PENDING_FILE):
        save_pending([])
        print(f"✅ pending.json erstellt")

    print(f"✅ Dashboard initialisiert: {DASHBOARD_DIR}")
    print(f"   Starte Server: python3 {os.path.abspath(__file__)} serve > ~/dashboard.log 2>&1 &")


def cmd_serve():
    if not os.path.exists(os.path.join(DASHBOARD_DIR, "index.html")):
        print("❌ Dashboard nicht initialisiert. Erst 'init' ausführen.")
        sys.exit(1)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    os.chdir(DASHBOARD_DIR)
    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True
    server = ReusableHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"🦞 Dashboard Server auf Port {PORT}")

    def shutdown(sig, frame):
        server.shutdown()
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        shutdown(None, None)


def cmd_update_widget(widget_id, json_str):
    """Update widget mit strikter Struktur-Validierung"""
    data = load_data()
    try:
        input_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ Ungültiges JSON: {e}")
        sys.exit(1)

    found = False
    existing_widget = None
    existing_index = -1
    for i, w in enumerate(data["widgets"]):
        if w["id"] == widget_id:
            found = True
            existing_widget = w
            existing_index = i
            break

    widget = normalize_widget_input(widget_id, input_data, existing_widget)

    if not found:
        widget.setdefault("position", len(data["widgets"]))

    # === Speichern ===
    if found:
        data["widgets"][existing_index] = widget
    else:
        data["widgets"].append(widget)

    save_data(data)
    
    # Debug-Output
    print(f"✅ Widget '{widget_id}' {'aktualisiert' if found else 'hinzugefügt'}")
    print(f"   Type: {widget.get('type')}")
    print(f"   Data-Keys: {list(widget.get('data', {}).keys())}")


def cmd_remove_widget(widget_id):
    data = load_data()
    before = len(data["widgets"])
    data["widgets"] = [w for w in data["widgets"] if w["id"] != widget_id]
    if len(data["widgets"]) < before:
        save_data(data)
        print(f"✅ Widget '{widget_id}' entfernt")
    else:
        print(f"⚠️ Widget '{widget_id}' nicht gefunden")


def cmd_add_button(button_id, label, action, icon="🔘", description=""):
    data = load_data()
    btn = {"id": button_id, "label": label, "action": action, "icon": icon, "description": description}

    found = False
    for i, b in enumerate(data["buttons"]):
        if b["id"] == button_id:
            data["buttons"][i] = btn
            found = True
            break

    if not found:
        data["buttons"].append(btn)

    save_data(data)
    print(f"✅ Button '{label}' {'aktualisiert' if found else 'hinzugefügt'}")


def cmd_remove_button(button_id):
    data = load_data()
    before = len(data["buttons"])
    data["buttons"] = [b for b in data["buttons"] if b["id"] != button_id]
    if len(data["buttons"]) < before:
        save_data(data)
        print(f"✅ Button '{button_id}' entfernt")
    else:
        print(f"⚠️ Button '{button_id}' nicht gefunden")


def cmd_set_status(status):
    data = load_data()
    data["meta"]["agent_status"] = status
    save_data(data)
    print(f"✅ Agent-Status: {status}")


def cmd_set_message(message):
    data = load_data()
    data["meta"]["agent_message"] = message
    save_data(data)
    print(f"✅ Agent-Nachricht gesetzt")


def cmd_notify(message, level="info"):
    data = load_data()
    notif = {
        "id": f"n-{int(time.time())}",
        "message": message,
        "level": level,
        "timestamp": now_iso()
    }
    data.setdefault("notifications", [])
    data["notifications"].append(notif)
    data["notifications"] = data["notifications"][-10:]
    save_data(data)
    print(f"✅ Benachrichtigung gesendet")


def cmd_pending():
    pending = load_pending()
    if not pending:
        print("✅ Keine ausstehenden Befehle")
        return
    print(f"📋 {len(pending)} ausstehende(r) Befehl(e):")
    for p in pending:
        print(f"  [{p['id']}] action={p['action']} button={p.get('button_label','?')} time={p['timestamp']}")


def cmd_clear_pending(cmd_id=None):
    pending = load_pending()
    if cmd_id:
        pending = [p for p in pending if p["id"] != cmd_id]
    else:
        pending = []
    save_pending(pending)
    print(f"✅ Pending {'gelöscht: ' + cmd_id if cmd_id else 'alle gelöscht'}")


def cmd_deploy_template():
    """Kopiere Template nach Dashboard-Dir (Fallback/Offline)"""
    src = os.path.join(TEMPLATE_DIR, "index.html")
    dst = os.path.join(DASHBOARD_DIR, "index.html")
    if os.path.exists(src):
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
            print(f"Template deployed: {dst}")
        else:
            print("Template ist aktuell")
    else:
        print(f"Template nicht gefunden: {src}")


def cmd_stop():
    """Server stoppen."""
    stopped = False
    
    # 1. Try PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            for _ in range(15):
                time.sleep(0.2)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
            else:
                os.kill(pid, signal.SIGKILL)
            stopped = True
            print(f"Server gestoppt (PID {pid})")
        except (ProcessLookupError, ValueError, OSError):
            pass
    
    # 2. Kill anything on the port
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{PORT}"],
            capture_output=True, text=True, timeout=3
        )
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and line.isdigit():
                try:
                    os.kill(int(line), signal.SIGKILL)
                    stopped = True
                except (ProcessLookupError, ValueError):
                    pass
    except Exception:
        pass
    
    # 3. Kill by process name (catch nohup wrappers etc)
    try:
        subprocess.run(
            ["pkill", "-f", "dashboard.py serve"],
            capture_output=True, timeout=3
        )
    except Exception:
        pass
    
    # Cleanup
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    
    if not stopped:
        print("Kein Server aktiv")


def cmd_start():
    """Server im Hintergrund starten (via subprocess)."""
    # Check if already running
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"Server laeuft bereits (PID {pid})")
            return
        except (ProcessLookupError, ValueError, OSError):
            pass

    # Also check if port is in use
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("127.0.0.1", PORT))
        s.close()
        print(f"Port {PORT} bereits belegt (anderer Prozess?)")
        return
    except (ConnectionRefusedError, socket.timeout, OSError):
        pass  # Port is free, good

    # Start server as background subprocess
    log_path = os.path.join(HOME, "dashboard.log")
    log_fd = open(log_path, "a")
    script = os.path.abspath(__file__)
    
    proc = subprocess.Popen(
        [sys.executable, script, "serve"],
        stdout=log_fd,
        stderr=log_fd,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=DASHBOARD_DIR
    )
    
    # Wait briefly to verify it started
    time.sleep(1.5)
    if proc.poll() is None:
        print(f"Server gestartet (PID {proc.pid}, Port {PORT})")
    else:
        print(f"Server-Start fehlgeschlagen (exit={proc.returncode}), siehe ~/dashboard.log")


def cmd_restart():
    """Server stoppen und neu starten."""
    cmd_stop()
    time.sleep(1)
    cmd_start()


def cmd_health():
    """Pruefe ob Server auf Port antwortet."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", PORT))
        s.close()
        print(f"OK: Port {PORT} antwortet")
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        print(f"FAIL: Port {PORT} antwortet nicht")
        return False


def cmd_sync_data():
    """Synchronisiere Dashboard mit Kalender, TODOs und Haushalt"""
    data = load_data()

    # === Single source: haushalt.py json ===
    try:
        result = subprocess.run(
            ["python3", os.path.join(WORKSPACE, "skills/haushalt/scripts/haushalt.py"), "json"],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=WORKSPACE
        )
        if result.returncode != 0:
            print(f"❌ sync-data fehlgeschlagen: {result.stdout or result.stderr}")
            sys.exit(1)

        payload = json.loads(result.stdout)

        tasks = payload.get("tasks", [])
        todos = payload.get("todos", [])
        events = payload.get("events", [])

        task_items = [
            {"text": t.get("display", ""), "done": bool(t.get("done", False))}
            for t in tasks
        ]

        todo_items = [
            {
                "text": t.get("text", ""),
                **({"deadline": t["deadline"]} if t.get("deadline") else {}),
            }
            for t in todos
        ]

        calendar_events = []
        for e in events:
            start = str(e.get("start", ""))
            date_part = start[:10] if len(start) >= 10 else ""
            time_part = start[11:16] if len(start) >= 16 else ""
            calendar_events.append({
                "date": date_part,
                "time": time_part,
                "title": e.get("summary", ""),
                "description": e.get("file", ""),
            })

        for w in data.get("widgets", []):
            if w.get("id") == "tasks":
                w.setdefault("data", {})["items"] = task_items
            elif w.get("id") == "todos":
                w.setdefault("data", {})["items"] = todo_items
            elif w.get("id") == "calendar":
                w.setdefault("data", {})["events"] = calendar_events[:10]

        # Agent behavior metrics
        metrics_result = subprocess.run(
            ["python3", os.path.join(WORKSPACE, "tools/agent_metrics.py")],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=WORKSPACE,
            env={**os.environ, "PICOCLAW_WORKSPACE": WORKSPACE},
        )
        if metrics_result.returncode == 0:
            metrics = json.loads(metrics_result.stdout)
            metric_items = [
                {
                    "label": "Skill Hit Rate",
                    "value": f"{round(float(metrics.get('skill_hit_rate', 0.0)) * 100, 1)}%",
                    "status": "ok" if float(metrics.get("skill_hit_rate", 0.0)) >= 0.8 else "warn",
                },
                {
                    "label": "Ad-hoc Exec Rate",
                    "value": f"{round(float(metrics.get('ad_hoc_exec_rate', 0.0)) * 100, 1)}%",
                    "status": "ok" if float(metrics.get("ad_hoc_exec_rate", 0.0)) <= 0.2 else "warn",
                },
                {
                    "label": "Retry Signal Rate",
                    "value": f"{round(float(metrics.get('retry_rate', 0.0)) * 100, 1)}%",
                    "status": "ok" if float(metrics.get("retry_rate", 0.0)) <= 0.1 else "warn",
                },
                {
                    "label": "Tool Calls",
                    "value": str(metrics.get("tool_calls", 0)),
                    "status": "ok",
                },
            ]

            metric_widget = {
                "id": "agent-metrics",
                "type": "status",
                "title": "Agent Behavior",
                "size": "medium",
                "data": {
                    "items": metric_items,
                    "generated_at": metrics.get("generated_at", ""),
                },
            }

            found = False
            for i, w in enumerate(data.get("widgets", [])):
                if w.get("id") == "agent-metrics":
                    data["widgets"][i] = normalize_widget_input("agent-metrics", metric_widget, w)
                    found = True
                    break
            if not found:
                metric_widget["position"] = len(data.get("widgets", []))
                data.setdefault("widgets", []).append(normalize_widget_input("agent-metrics", metric_widget, None))

    except json.JSONDecodeError as e:
        print(f"❌ sync-data JSON-Fehler: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ sync-data Fehler: {e}")
        sys.exit(1)
    
    save_data(data)
    print(f"✅ Dashboard synchronisiert")


def parse_calendar_output(output):
    """Parse haushalt.py cal Output zu Events."""
    import re

    events = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Heute:") or line.startswith("📅") or line.startswith("OK:"):
            continue

        match = re.match(
            r'^(?P<date>(?:Mo|Di|Mi|Do|Fr|Sa|So)\s+\d{2}\.\d{2}\.)\s+'
            r'(?P<time>\d{2}:\d{2}(?:-\d{2}:\d{2})?)\s+'
            r'(?P<title>.+?)'
            r'(?:\s+\[(?P<source>[^\]]+)\])?\s*$',
            line,
        )
        if not match:
            continue

        title = (match.group("title") or "").strip()
        source = (match.group("source") or "").strip()
        events.append(
            {
                "date": match.group("date"),
                "time": match.group("time"),
                "title": title,
                "description": source,
            }
        )

    return events[:10]

def parse_todo_output(output):
    """Parse haushalt.py todo-list Output zu TODO-Items."""
    import re

    todos = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Heute:") or line.startswith("📋"):
            continue

        match = re.match(
            r'^\d+[\.)]\s+'
            r'(?P<text>.+?)'
            r'(?:\s+\(bis\s+(?P<deadline>[^)]+)\))?'
            r'(?:\s+\[(?P<age>[^\]]+)\])?\s*$',
            line,
        )
        if not match:
            continue

        item = {"text": (match.group("text") or "").strip()}
        deadline = (match.group("deadline") or "").strip()
        age = (match.group("age") or "").strip()
        if deadline:
            item["deadline"] = deadline
        if age:
            item["age"] = age
        todos.append(item)

    return todos


def _is_exec_allowed(command):
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False
    return parts[0] in EXEC_ALLOWLIST

def cmd_ensure_running():
    cmd_deploy_template()
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"✅ Dashboard-Server läuft (PID {pid}, Port {PORT})")
            return
        except (ProcessLookupError, ValueError, OSError):
            pass

    print(f"⚠️ Dashboard-Server nicht aktiv")
    print("Dashboard-Server nicht aktiv, starte...")
    cmd_start()


def cmd_status():
    data = load_data()
    pending = load_pending()

    server_status = "❌ offline"
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            server_status = f"✅ online (PID {pid})"
        except (ProcessLookupError, ValueError, OSError):
            server_status = "❌ offline (stale PID)"

    print(f"🦞 PicoClaw Dashboard")
    print(f"   Server:    {server_status}")
    print(f"   URL:       http://192.168.2.50:{PORT}/")
    print(f"   Widgets:   {len(data['widgets'])}")
    print(f"   Buttons:   {len(data['buttons'])}")
    print(f"   Pending:   {len(pending)}")
    print(f"   Updated:   {data['meta']['updated']}")
    print(f"   Status:    {data['meta']['agent_status']}")


# === HTTP Server ===

class DashboardHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress to save resources

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/data.json":
            self._serve_json_file(DATA_FILE)
        elif path == "/pending.json":
            self._serve_json_file(PENDING_FILE)
        elif path == "/" or path == "/index.html":
            # IMMER index.html aus Template-Dir laden (Source of Truth)
            template = os.path.join(TEMPLATE_DIR, "index.html")
            fallback = os.path.join(DASHBOARD_DIR, "index.html")
            html_path = template if os.path.exists(template) else fallback
            try:
                with open(html_path, "rb") as f:
                    html = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(html)
            except FileNotFoundError:
                self.send_error(404, "index.html not found")
        else:
            super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/action":
            self._handle_action()
        elif path == "/api/dismiss":
            self._handle_dismiss()
        elif path == "/api/exec":
            self._handle_exec()
        else:
            self.send_error(404)

    def _serve_json_file(self, filepath):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)

    def _send_json(self, data):
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length)) if length > 0 else {}
        except (json.JSONDecodeError, ValueError):
            return None

    def _handle_action(self):
        body = self._read_body()
        if body is None:
            self.send_error(400, "Invalid JSON")
            return

        action = body.get("action", "")
        
        # === Spezial-Handler für haushalt-task-done ===
        if action == "haushalt-task-done":
            task_text = body.get("task_text", "")
            if not task_text:
                self._send_json({"status": "error", "message": "task_text erforderlich"})
                return
            
            # Rufe haushalt.py erledigt auf
            try:
                result = subprocess.run(
                    ["python3", os.path.join(WORKSPACE, "skills/haushalt/scripts/haushalt.py"), "erledigt", task_text],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=WORKSPACE
                )
                if result.returncode == 0:
                    # Erfolg — aktualisiere tasks-Widget
                    self._update_tasks_widget()
                    self._send_json({"status": "queued", "id": f"task-{int(time.time())}", "message": f"✅ {task_text} erledigt"})
                else:
                    self._send_json({"status": "error", "message": result.stderr or "Fehler beim Abhaken"})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
            return

        # === Spezial-Handler für haushalt-todo-done ===
        if action == "haushalt-todo-done":
            todo_text = body.get("todo_text", "")
            if not todo_text:
                self._send_json({"status": "error", "message": "todo_text erforderlich"})
                return

            try:
                result = subprocess.run(
                    ["python3", os.path.join(WORKSPACE, "skills/haushalt/scripts/haushalt.py"), "todo-done", todo_text],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=WORKSPACE,
                )
                if result.returncode == 0:
                    self._update_todos_widget()
                    self._send_json({"status": "queued", "id": f"todo-{int(time.time())}", "message": f"✅ {todo_text} erledigt"})
                else:
                    self._send_json({"status": "error", "message": (result.stderr or result.stdout or "Fehler beim TODO-Abhaken").strip()})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
            return

        # === Spezial-Handler für Galerie-Interaktionen ===
        if action in {"gallery-refresh", "gallery-navigate", "gallery-jump", "gallery-toggle-autoplay"}:
            try:
                if action == "gallery-refresh":
                    ok, result = self._refresh_gallery_widget()
                    if ok:
                        self._send_json({"status": "ok", "id": f"gallery-{int(time.time())}", "data": result})
                    else:
                        self._send_json({"status": "error", "message": result})
                elif action == "gallery-navigate":
                    direction = str(body.get("direction") or body.get("value") or "next").strip().lower()
                    if direction not in {"next", "prev"}:
                        direction = "next"
                    ok, result = self._run_gallery_command("navigate", direction)
                    if not ok:
                        self._send_json({"status": "error", "message": result})
                        return
                    ok, refreshed = self._refresh_gallery_widget()
                    if ok:
                        self._send_json({"status": "ok", "id": f"gallery-{int(time.time())}", "data": refreshed})
                    else:
                        self._send_json({"status": "error", "message": refreshed})
                elif action == "gallery-jump":
                    index = body.get("index", body.get("value", 0))
                    try:
                        index = int(index)
                    except (TypeError, ValueError):
                        self._send_json({"status": "error", "message": "index muss eine Zahl sein"})
                        return
                    ok, result = self._run_gallery_command("jump", str(index))
                    if not ok:
                        self._send_json({"status": "error", "message": result})
                        return
                    ok, refreshed = self._refresh_gallery_widget()
                    if ok:
                        self._send_json({"status": "ok", "id": f"gallery-{int(time.time())}", "data": refreshed})
                    else:
                        self._send_json({"status": "error", "message": refreshed})
                elif action == "gallery-toggle-autoplay":
                    ok, result = self._run_gallery_command("autoplay")
                    if not ok:
                        self._send_json({"status": "error", "message": result})
                        return
                    ok, refreshed = self._refresh_gallery_widget()
                    if ok:
                        self._send_json({"status": "ok", "id": f"gallery-{int(time.time())}", "data": refreshed})
                    else:
                        self._send_json({"status": "error", "message": refreshed})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)})
            return

        # === Standard-Action: In pending Queue ===
        cmd = {
            "id": f"cmd-{int(time.time())}",
            "action": action,
            "button_id": body.get("button_id", ""),
            "button_label": body.get("button_label", ""),
            "timestamp": now_iso(),
            "status": "pending"
        }

        pending = load_pending()
        pending.append(cmd)
        save_pending(pending)
        self._send_json({"status": "queued", "id": cmd["id"]})

    def _update_tasks_widget(self):
        """Aktualisiere das tasks-Widget mit aktuellen Haushalt-Daten"""
        try:
            result = subprocess.run(
                ["python3", os.path.join(WORKSPACE, "skills/haushalt/scripts/haushalt.py"), "json"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=WORKSPACE
            )
            if result.returncode == 0:
                haushalt_data = json.loads(result.stdout)
                tasks = haushalt_data.get("tasks", [])
                
                # Konvertiere zu Dashboard-Format (haushalt-json hat "display" Feld)
                items = [{"text": t.get("display", t.get("name", "")), "done": t.get("done", False)} for t in tasks]
                
                data = load_data()
                for i, w in enumerate(data["widgets"]):
                    if w["id"] == "tasks":
                        w.setdefault("data", {})["items"] = items
                        break
                save_data(data)
        except Exception as e:
            pass  # Silent fail — Widget wird bei nächstem Refresh aktualisiert

    def _update_todos_widget(self):
        """Aktualisiere das todos-Widget mit aktuellen TODO-Daten"""
        try:
            result = subprocess.run(
                ["python3", os.path.join(WORKSPACE, "skills/haushalt/scripts/haushalt.py"), "todo-list"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=WORKSPACE,
            )
            if result.returncode == 0:
                todos = parse_todo_output(result.stdout)

                data = load_data()
                for i, w in enumerate(data["widgets"]):
                    if w["id"] == "todos":
                        w.setdefault("data", {})["items"] = todos
                        break
                save_data(data)
        except Exception:
            pass

    def _run_gallery_command(self, command, *args):
        gallery_script = os.path.join(WORKSPACE, "skills/dashboard/scripts/gallery.py")
        cmd = ["python3", gallery_script, command, *args]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=8,
            cwd=WORKSPACE,
        )

        output = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or output or f"gallery.py {command} fehlgeschlagen").strip()
            return False, err

        if not output:
            return True, {}

        try:
            return True, json.loads(output)
        except json.JSONDecodeError:
            return False, f"Ungültige gallery.py Antwort: {output[:200]}"

    def _refresh_gallery_widget(self):
        ok, widget = self._run_gallery_command("get")
        if not ok:
            return False, widget

        try:
            cmd_update_widget("gallery", json.dumps(widget, ensure_ascii=False))
            return True, {
                "widget": "gallery",
                "images": len(widget.get("data", {}).get("images", [])),
                "currentIndex": widget.get("data", {}).get("currentIndex", 0),
            }
        except Exception as e:
            return False, str(e)

    def _handle_dismiss(self):
        body = self._read_body()
        if body is None:
            self.send_error(400)
            return

        notif_id = body.get("id", "")
        data = load_data()
        data["notifications"] = [n for n in data.get("notifications", []) if n["id"] != notif_id]
        save_data(data)
        self._send_json({"status": "dismissed"})

    def _handle_exec(self):
        """Führe Shell-Befehl aus und gebe Output zurück"""
        if not EXEC_ENABLED:
            self._send_json({
                "output": "",
                "error": "Dashboard exec ist deaktiviert (DASHBOARD_EXEC_ENABLED=1 zum Aktivieren)",
                "returncode": -1,
            })
            return

        body = self._read_body()
        if body is None:
            self.send_error(400)
            return

        command = body.get("command", "").strip()
        if not command:
            self._send_json({"output": "", "error": "Leerer Befehl"})
            return

        if not _is_exec_allowed(command):
            self._send_json({
                "output": "",
                "error": f"Befehl nicht erlaubt (Allowlist): {sorted(EXEC_ALLOWLIST)}",
                "returncode": -1,
            })
            return

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.path.expanduser("~")
            )
            output = result.stdout + (result.stderr if result.returncode != 0 else "")
            self._send_json({"output": output.strip(), "error": None, "returncode": result.returncode})
        except subprocess.TimeoutExpired:
            self._send_json({"output": "", "error": "Timeout (10s)", "returncode": -1})
        except Exception as e:
            self._send_json({"output": "", "error": str(e), "returncode": -1})


# === Main ===

def usage():
    print("""PicoClaw Dashboard Manager 🦞

  init                              Dashboard initialisieren
  serve                             HTTP-Server starten (Vordergrund)
  start                             Server im Hintergrund starten
  stop                              Server stoppen
  restart                           Server neu starten (stop + start)
  health                            Pruefe ob Port 7000 antwortet
  ensure-running                    Prüfen ob Server läuft
  status                            Dashboard-Status anzeigen
  update-widget <id> '<json>'       Widget aktualisieren/erstellen
  remove-widget <id>                Widget entfernen
    save-widget-template <id> [name]  Widget als Template speichern
    export-widget-templates           Alle Widgets als Templates exportieren
    list-widget-templates             Verfügbare Widget-Templates anzeigen
    apply-widget-template <name> [id] Template auf Widget anwenden
  add-button <id> <label> <action> [icon] [desc]  Button hinzufügen
  remove-button <id>                Button entfernen
  set-status <online|offline|busy>  Agent-Status setzen
  set-message '<text>'              Agent-Nachricht setzen
  notify '<text>' [level]           Benachrichtigung senden
  pending                           Ausstehende Befehle anzeigen
  clear-pending [id]                Ausstehende Befehle löschen""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    c = sys.argv[1]

    if c == "init":
        cmd_init()
    elif c == "serve":
        cmd_serve()
    elif c == "start":
        cmd_start()
    elif c == "stop":
        cmd_stop()
    elif c == "restart":
        cmd_restart()
    elif c == "health":
        cmd_health()
    elif c == "ensure-running":
        cmd_ensure_running()
    elif c == "deploy-template":
        cmd_deploy_template()
    elif c == "status":
        cmd_status()
    elif c == "update-widget":
        if len(sys.argv) < 4:
            print("Usage: update-widget <id> '<json>'")
            sys.exit(1)
        cmd_update_widget(sys.argv[2], sys.argv[3])
    elif c == "remove-widget":
        if len(sys.argv) < 3:
            sys.exit(1)
        cmd_remove_widget(sys.argv[2])
    elif c == "save-widget-template":
        if len(sys.argv) < 3:
            print("Usage: save-widget-template <widget-id> [template-name]")
            sys.exit(1)
        cmd_save_widget_template(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif c == "export-widget-templates":
        cmd_export_widget_templates()
    elif c == "list-widget-templates":
        cmd_list_widget_templates()
    elif c == "apply-widget-template":
        if len(sys.argv) < 3:
            print("Usage: apply-widget-template <template-name> [widget-id]")
            sys.exit(1)
        cmd_apply_widget_template(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif c == "add-button":
        if len(sys.argv) < 5:
            print("Usage: add-button <id> <label> <action> [icon] [desc]")
            sys.exit(1)
        icon = sys.argv[5] if len(sys.argv) > 5 else "🔘"
        desc = sys.argv[6] if len(sys.argv) > 6 else ""
        cmd_add_button(sys.argv[2], sys.argv[3], sys.argv[4], icon, desc)
    elif c == "remove-button":
        if len(sys.argv) < 3:
            sys.exit(1)
        cmd_remove_button(sys.argv[2])
    elif c == "set-status":
        if len(sys.argv) < 3:
            sys.exit(1)
        cmd_set_status(sys.argv[2])
    elif c == "set-message":
        if len(sys.argv) < 3:
            sys.exit(1)
        cmd_set_message(" ".join(sys.argv[2:]))
    elif c == "notify":
        if len(sys.argv) < 3:
            sys.exit(1)
        level = sys.argv[3] if len(sys.argv) > 3 else "info"
        cmd_notify(sys.argv[2], level)
    elif c == "pending":
        cmd_pending()
    elif c == "clear-pending":
        cmd_clear_pending(sys.argv[2] if len(sys.argv) > 2 else None)
    elif c == "sync-data":
        cmd_sync_data()
    else:
        print(f"❌ Unbekannter Befehl: {c}")
        usage()
        sys.exit(1)

#!/usr/bin/env python3
"""Dashboard Watchdog 🦞
Überwacht den Dashboard-Webserver und stellt sicher, dass er immer läuft.

Funktionen:
  - Health-Check (HTTP GET auf Port 7000)
  - Automatischer Neustart bei Fehler
  - Logging und Status-Tracking
  - Cron-Integration für regelmäßige Checks

Befehle:
  python3 watchdog.py health-check    # Prüfe ob Server läuft
  python3 watchdog.py ensure-running  # Starte Server falls down
  python3 watchdog.py status          # Zeige Watchdog-Status
  python3 watchdog.py install-cron    # Installiere Cron-Job (alle 2 Min)
  python3 watchdog.py remove-cron     # Entferne Cron-Job
  python3 watchdog.py logs            # Zeige letzte Logs
"""

import json
import os
import sys
import time
import datetime
import subprocess
import signal
import socket
import urllib.request
import urllib.error
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

# === Configuration ===
HOME = os.path.expanduser("~")
WORKSPACE = os.path.join(HOME, ".picoclaw", "workspace")
DASHBOARD_DIR = os.path.join(WORKSPACE, "dashboard")
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
DASHBOARD_SCRIPT = os.path.join(SCRIPTS_DIR, "dashboard.py")

PORT = 7000
PID_FILE = os.path.join(DASHBOARD_DIR, "server.pid")
WATCHDOG_LOG = os.path.join(DASHBOARD_DIR, "watchdog.log")
WATCHDOG_ERROR_LOG = os.path.join(DASHBOARD_DIR, "watchdog-error.log")
WATCHDOG_STATE = os.path.join(DASHBOARD_DIR, "watchdog-state.json")
WATCHDOG_LOCK = os.path.join(DASHBOARD_DIR, "watchdog.lock")
WATCHDOG_CRON_LOG = os.path.join(DASHBOARD_DIR, "watchdog-cron.log")
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable or "python3")

# Max Restart Attempts in 10 Minuten (um Crash-Loops zu vermeiden)
MAX_RESTARTS_PER_WINDOW = 5
RESTART_WINDOW_MINUTES = 10


def log_event(level, message):
    """Schreibe Log-Eintrag mit Timestamp"""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level:8s}] {message}"
    print(log_entry)
    
    try:
        with open(WATCHDOG_LOG, "a") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"[ERROR] Konnte nicht in Watchdog-Log schreiben: {e}")


def log_error(message):
    timestamp = datetime.datetime.now().isoformat()
    entry = f"[{timestamp}] {message}"
    try:
        with open(WATCHDOG_ERROR_LOG, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass


def acquire_lock():
    os.makedirs(DASHBOARD_DIR, exist_ok=True)
    lock_handle = open(WATCHDOG_LOCK, "w")
    if fcntl is not None:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            lock_handle.close()
            return None
    return lock_handle


def release_lock(lock_handle):
    if not lock_handle:
        return
    try:
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        lock_handle.close()
    except Exception:
        pass


def read_state():
    """Lese Watchdog-State (Restart-Count, etc.)"""
    if not os.path.exists(WATCHDOG_STATE):
        return {
            "last_check": None,
            "last_restart": None,
            "restart_count": 0,
            "restart_times": [],
            "status": "unknown"
        }
    
    try:
        with open(WATCHDOG_STATE, "r") as f:
            return json.load(f)
    except:
        return {
            "last_check": None,
            "last_restart": None,
            "restart_count": 0,
            "restart_times": [],
            "status": "unknown"
        }


def write_state(state):
    """Schreibe Watchdog-State"""
    try:
        with open(WATCHDOG_STATE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log_event("ERROR", f"Konnte State nicht schreiben: {e}")


def is_server_running():
    """Prüfe ob Server auf Port 7000 antwortet"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=3) as response:
            return 200 <= int(response.status) < 500
    except (urllib.error.URLError, socket.timeout, ValueError):
        return False


def get_server_pid():
    """Lese Server-PID aus PID-Datei"""
    if not os.path.exists(PID_FILE):
        return None
    
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
            # Prüfe ob Prozess existiert
            os.kill(pid, 0)  # Signal 0 = nur prüfen
            return pid
    except:
        return None


def start_server():
    """Starte Dashboard-Server"""
    try:
        result = subprocess.run(
            [PYTHON_BIN, DASHBOARD_SCRIPT, "start"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=WORKSPACE,
        )
        if result.returncode == 0:
            log_event("INFO", "Dashboard-Server gestartet via dashboard.py start")
            if result.stdout.strip():
                log_event("INFO", result.stdout.strip().splitlines()[-1])
            time.sleep(2)
            return True

        details = (result.stderr or result.stdout or "Unbekannter Startfehler").strip()
        log_event("ERROR", f"Serverstart fehlgeschlagen: {details[:240]}")
        log_error(f"start_server failed: return={result.returncode} details={details}")
        return False
    except Exception as e:
        log_event("ERROR", f"Konnte Server nicht starten: {e}")
        log_error(f"start_server exception: {e}")
        return False


def stop_server(pid=None):
    """Stoppe Dashboard-Server"""
    if pid is None:
        pid = get_server_pid()
    
    if pid is None:
        log_event("WARN", "Keine Server-PID gefunden, kann nicht stoppen")
        return False
    
    try:
        os.kill(pid, signal.SIGTERM)
        log_event("INFO", f"Server-Prozess {pid} mit SIGTERM beendet")
        time.sleep(1)
        
        # Prüfe ob Prozess noch läuft
        try:
            os.kill(pid, 0)
            # Noch am Leben, SIGKILL
            os.kill(pid, signal.SIGKILL)
            log_event("WARN", f"Server-Prozess {pid} mit SIGKILL beendet")
        except:
            pass  # Prozess ist weg
        
        return True
    except Exception as e:
        log_event("ERROR", f"Fehler beim Stoppen von PID {pid}: {e}")
        return False


def should_restart():
    """Prüfe ob zu viele Restarts in kurzer Zeit (Crash-Loop-Schutz)"""
    state = read_state()
    restart_times = state.get("restart_times", [])
    
    # Entferne alte Einträge außerhalb des Fensters
    now = time.time()
    window_start = now - (RESTART_WINDOW_MINUTES * 60)
    restart_times = [t for t in restart_times if t > window_start]
    
    if len(restart_times) >= MAX_RESTARTS_PER_WINDOW:
        log_event("ERROR", 
            f"Zu viele Restarts ({len(restart_times)}) in {RESTART_WINDOW_MINUTES} Min - "
            f"Crash-Loop erkannt! Starte nicht neu.")
        return False
    
    return True


def health_check():
    """Führe Health-Check durch"""
    state = read_state()
    state["last_check"] = datetime.datetime.now().isoformat()
    
    if is_server_running():
        log_event("OK", "Server antwortet auf Port 7000")
        state["status"] = "online"
        write_state(state)
        return True
    else:
        log_event("ERROR", "Server antwortet NICHT auf Port 7000")
        state["status"] = "offline"
        write_state(state)
        return False


def ensure_running():
    """Stelle sicher dass Server läuft, starte ihn sonst neu"""
    log_event("INFO", "=== Watchdog Check ===")
    
    if health_check():
        return True
    
    # Server ist down
    log_event("WARN", "Server ist down, versuche Neustart...")
    
    if not should_restart():
        return False
    
    # Stoppe alten Prozess falls noch vorhanden
    old_pid = get_server_pid()
    if old_pid:
        stop_server(old_pid)
    
    # Starte neuen Server
    if start_server():
        # Prüfe ob Server tatsächlich gestartet ist
        time.sleep(3)
        if health_check():
            state = read_state()
            state["last_restart"] = datetime.datetime.now().isoformat()
            state["restart_count"] = state.get("restart_count", 0) + 1
            
            # Füge zu Restart-Times hinzu
            restart_times = state.get("restart_times", [])
            restart_times.append(time.time())
            state["restart_times"] = restart_times
            
            log_event("OK", f"Server erfolgreich neu gestartet (#{state['restart_count']})")
            write_state(state)
            return True
        else:
            log_event("ERROR", "Server konnte nicht erfolgreich neu gestartet werden")
            return False
    
    return False


def show_status():
    """Zeige Watchdog-Status"""
    state = read_state()
    
    print("\n=== Dashboard Watchdog Status ===")
    print(f"Status:           {state.get('status', 'unknown').upper()}")
    print(f"Letzte Prüfung:   {state.get('last_check', 'nie')}")
    print(f"Letzter Neustart: {state.get('last_restart', 'nie')}")
    print(f"Restart-Count:    {state.get('restart_count', 0)}")
    
    restart_times = state.get("restart_times", [])
    if restart_times:
        now = time.time()
        window_start = now - (RESTART_WINDOW_MINUTES * 60)
        recent = [t for t in restart_times if t > window_start]
        print(f"Restarts in letzten {RESTART_WINDOW_MINUTES} Min: {len(recent)}/{MAX_RESTARTS_PER_WINDOW}")
    
    print(f"Server-PID:       {get_server_pid() or 'nicht gefunden'}")
    print(f"Watchdog-Log:     {WATCHDOG_LOG}")
    print(f"Watchdog-State:   {WATCHDOG_STATE}")
    print()


def show_logs(lines=20):
    """Zeige letzte Log-Einträge"""
    if not os.path.exists(WATCHDOG_LOG):
        print("Keine Logs vorhanden")
        return
    
    try:
        with open(WATCHDOG_LOG, "r") as f:
            all_lines = f.readlines()
        
        print(f"\n=== Letzte {lines} Watchdog-Logs ===")
        for line in all_lines[-lines:]:
            print(line.rstrip())
        print()
    except Exception as e:
        print(f"Fehler beim Lesen der Logs: {e}")


def install_cron():
    """Installiere Cron-Job für regelmäßige Checks (alle 2 Minuten)"""
    cron_cmd = (
        f"cd {WORKSPACE} && "
        f"{PYTHON_BIN} {os.path.abspath(__file__)} ensure-running "
        f">> {WATCHDOG_CRON_LOG} 2>&1"
    )
    
    # Prüfe ob Job schon existiert
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )
        existing = result.stdout
        if "dashboard/scripts/watchdog.py" in existing:
            print("Watchdog Cron-Job existiert bereits")
            return
    except:
        pass
    
    # Füge neuen Job hinzu
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )
        existing = result.stdout or ""
    except:
        existing = ""
    
    # Neuer Job: Alle 2 Minuten
    new_job = f"*/2 * * * * {cron_cmd}\n"
    
    try:
        new_crontab = existing + new_job
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(new_crontab)
        
        if process.returncode == 0:
            log_event("OK", "Watchdog Cron-Job installiert (*/2 * * * *)")
            print("✓ Watchdog läuft jetzt alle 2 Minuten")
        else:
            print(f"Fehler beim Installieren des Cron-Jobs: {stderr}")
    except Exception as e:
        print(f"Fehler: {e}")


def remove_cron():
    """Entferne Cron-Job"""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )
        existing = result.stdout or ""
    except:
        print("Keine Crontab gefunden")
        return
    
    # Entferne Watchdog-Zeile
    lines = [line for line in existing.split("\n") 
             if "watchdog.py" not in line or line.strip() == ""]
    
    new_crontab = "\n".join(lines)
    
    try:
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(new_crontab)
        
        if process.returncode == 0:
            log_event("OK", "Watchdog Cron-Job entfernt")
            print("✓ Watchdog Cron-Job entfernt")
        else:
            print(f"Fehler: {stderr}")
    except Exception as e:
        print(f"Fehler: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "health-check":
        lock_handle = acquire_lock()
        if lock_handle is None:
            log_event("WARN", "Watchdog-Lock aktiv, health-check wird übersprungen")
            sys.exit(0)
        try:
            sys.exit(0 if health_check() else 1)
        finally:
            release_lock(lock_handle)
    
    elif command == "ensure-running":
        lock_handle = acquire_lock()
        if lock_handle is None:
            log_event("WARN", "Watchdog-Lock aktiv, ensure-running wird übersprungen")
            sys.exit(0)
        try:
            sys.exit(0 if ensure_running() else 1)
        finally:
            release_lock(lock_handle)
    
    elif command == "status":
        show_status()
    
    elif command == "logs":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_logs(lines)
    
    elif command == "install-cron":
        install_cron()
    
    elif command == "remove-cron":
        remove_cron()
    
    else:
        print(f"Unbekannter Befehl: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

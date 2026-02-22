# Dashboard Watchdog Quick-Start 🦞

## TL;DR - Watchdog aktivieren

```bash
cd ~/.picoclaw/workspace
python3 skills/dashboard/scripts/watchdog.py install-cron
```

**Fertig!** Der Watchdog läuft jetzt automatisch alle 2 Minuten.

---

## Status prüfen

```bash
python3 skills/dashboard/scripts/watchdog.py status
```

Erwartet:
```
Status:           ONLINE
Letzte Prüfung:   2026-02-21T20:18:10.628652
Letzter Neustart: None
Restart-Count:    0
Server-PID:       15435
```

---

## Was macht der Watchdog?

| Aktion | Intervall | Effekt |
|--------|-----------|--------|
| Health-Check | 2 Minuten | Prüft ob Server antwortet |
| Auto-Restart | Bei Fehler | Startet Server neu |
| Logging | Jedes Event | Schreibt in `watchdog.log` |
| Crash-Loop-Schutz | Kontinuierlich | Stoppt nach 5 Restarts in 10 Min |

---

## Logs anzeigen

```bash
# Letzte 20 Logs (default)
python3 skills/dashboard/scripts/watchdog.py logs

# Letzte 50 Logs
python3 skills/dashboard/scripts/watchdog.py logs 50

# Echtzeit-Monitoring
tail -f ~/.picoclaw/workspace/dashboard/watchdog.log
```

---

## Wenn etwas schiefgeht

### Watchdog deaktivieren
```bash
python3 skills/dashboard/scripts/watchdog.py remove-cron
```

### Server manuell starten
```bash
python3 skills/dashboard/scripts/dashboard.py serve
```

### Crash-Loop-Schutz zurücksetzen
```bash
rm ~/.picoclaw/workspace/dashboard/watchdog-state.json
python3 skills/dashboard/scripts/watchdog.py ensure-running
```

---

## Überwachung

**Cron-Job prüfen:**
```bash
crontab -l | grep watchdog
```

**Server online?**
```bash
curl http://localhost:7000/
```

**Watchdog State anzeigen:**
```bash
cat ~/.picoclaw/workspace/dashboard/watchdog-state.json
```

---

## Dokumentation

Für Details siehe: `skills/dashboard/WATCHDOG.md`

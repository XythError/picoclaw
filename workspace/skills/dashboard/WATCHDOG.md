# Dashboard Watchdog 🦞

## Zweck
Der **Watchdog** überwacht den Dashboard-Webserver und stellt sicher, dass er immer läuft und Echtzeitinformationen bereitstellt.

**Automatische Funktionen:**
- ✅ Health-Check alle 2 Minuten (via Cron)
- ✅ Automatischer Neustart bei Fehler
- ✅ Crash-Loop-Schutz (max. 5 Restarts in 10 Min)
- ✅ Logging und Status-Tracking
- ✅ Persistent State Management

---

## Installation

### 1. Watchdog starten
```bash
cd ~/.picoclaw/workspace
python3 skills/dashboard/scripts/watchdog.py install-cron
```

Das installiert einen Cron-Job, der alle **2 Minuten** läuft.

### 2. Status prüfen
```bash
python3 skills/dashboard/scripts/watchdog.py status
```

Erwartet:
```
Status:           ONLINE
Letzte Prüfung:   2026-02-21T20:18:10.628652
Server-PID:       15435
```

---

## Befehle

| Befehl | Funktion |
|--------|----------|
| `health-check` | Prüfe ob Server läuft (HTTP GET auf Port 7000) |
| `ensure-running` | Starte Server falls down, sonst OK |
| `status` | Zeige Watchdog-Status und Statistiken |
| `logs [lines]` | Zeige letzte Log-Einträge (default: 20) |
| `install-cron` | Installiere Cron-Job (*/2 * * * *) |
| `remove-cron` | Entferne Cron-Job |

### Beispiele

```bash
# Manueller Health-Check
python3 scripts/watchdog.py health-check

# Manuelle Prüfung + ggf. Neustart
python3 scripts/watchdog.py ensure-running

# Status anzeigen
python3 scripts/watchdog.py status

# Letzte 50 Logs
python3 scripts/watchdog.py logs 50

# Cron deinstallieren
python3 scripts/watchdog.py remove-cron
```

---

## Wie es funktioniert

### Ablauf (alle 2 Minuten via Cron)
1. **Health-Check**: Sende HTTP GET auf `http://localhost:7000/`
2. **Wenn Server antwortet**: OK, weiter
3. **Wenn Server nicht antwortet**:
   - Prüfe Crash-Loop-Schutz (max. 5 Restarts in 10 Min)
   - Stoppe alten Prozess (falls noch vorhanden)
   - Starte neuen Server mit `dashboard.py serve`
   - Warte 3 Sekunden
   - Prüfe ob Server tatsächlich läuft

### State-Management
Der Watchdog speichert seinen State in `dashboard/watchdog-state.json`:
```json
{
  "status": "online",
  "last_check": "2026-02-21T20:18:10.628652",
  "last_restart": "2026-02-21T20:15:00.000000",
  "restart_count": 1,
  "restart_times": [1708545300.0, 1708545360.0]
}
```

### Logging
Alle Events werden in `dashboard/watchdog.log` geloggt:
```
[2026-02-21T20:18:10.654319] [OK      ] Server antwortet auf Port 7000
[2026-02-21T20:18:12.123456] [INFO    ] Dashboard-Server gestartet
[2026-02-21T20:18:15.789012] [OK      ] Server erfolgreich neu gestartet (#1)
```

---

## Crash-Loop-Schutz

Der Watchdog schützt vor Endlosschleifen:

**Regel:** Max. 5 Restarts in 10 Minuten

**Wenn überschritten:**
- Watchdog stoppt die Neustart-Versuche
- Log-Eintrag: `Crash-Loop erkannt! Starte nicht neu.`
- Manuelle Intervention erforderlich

**Lösung:**
```bash
# Prüfe Logs
python3 scripts/watchdog.py logs 50

# Untersuche Dashboard-Fehler
curl http://localhost:7000/

# Starte manuell neu
python3 scripts/dashboard.py restart

# Setze Restart-Counter zurück (optional)
rm dashboard/watchdog-state.json
python3 scripts/watchdog.py ensure-running
```

---

## Integration mit Dashboard-Skill

Der Watchdog ist **automatisch integriert** in die Dashboard-Skill-Befehle:

```bash
# Alle diese Befehle aktivieren den Watchdog implizit:
python3 skills/dashboard/scripts/dashboard.py ensure-running
python3 skills/dashboard/scripts/dashboard.py health
```

---

## Monitoring & Alerts

### Status-Check
```bash
python3 skills/dashboard/scripts/watchdog.py status
```

### Automatische Alerts (via n8n/Telegram)
Optional: Konfiguriere n8n um Watchdog-Fehler zu melden:
```bash
# Prüfe ob Watchdog-State "offline" ist
curl -s http://localhost:7000/data.json | grep -q '"status":"offline"' && \
  echo "🚨 Dashboard ist DOWN" | telegram-send --stdin
```

---

## Checkliste für Betrieb

- [ ] Watchdog installiert: `install-cron` ausgeführt
- [ ] Status online: `status` zeigt "ONLINE"
- [ ] Logs vorhanden: `logs` zeigt aktuelle Einträge
- [ ] Cron aktiv: `crontab -l | grep watchdog`
- [ ] Port 7000 erreichbar: `curl http://localhost:7000/`

---

## Troubleshooting

| Problem | Lösung |
|---------|--------|
| Watchdog läuft nicht | `crontab -l` prüfen, ggf. `install-cron` erneut ausführen |
| Server startet nicht neu | Logs prüfen: `logs 50`, manuell testen: `dashboard.py serve` |
| Crash-Loop erkannt | Logs analysieren, manuell fixen, `watchdog-state.json` löschen |
| Port 7000 nicht erreichbar | `netstat -tlnp \| grep 7000`, Firewall prüfen |
| Zu viele Restarts | Watchdog stoppt Neustarts (Schutz), manuell debuggen |

---

## Zukünftige Erweiterungen

- [ ] Automatische Telegram-Benachrichtigungen bei Fehler
- [ ] Metriken (Uptime %, Restart-Count) ins Dashboard
- [ ] Graceful Shutdown mit Daten-Backup
- [ ] Performance-Monitoring (RAM, CPU)
- [ ] Automatische Log-Rotation (nach 1 MB)

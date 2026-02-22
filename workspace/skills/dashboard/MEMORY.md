# Dashboard — Skill Memory

## Konfiguration
- **URL:** http://192.168.2.50:7000/
- **Port:** 7000
- **Daten:** ~/.picoclaw/workspace/dashboard/data.json
- **Pending:** ~/.picoclaw/workspace/dashboard/pending.json
- **Server-Log:** ~/dashboard.log
- **PID-File:** ~/.picoclaw/workspace/dashboard/server.pid

## Server starten
```bash
nohup python3 skills/dashboard/scripts/dashboard.py serve > ~/dashboard.log 2>&1 &
```

## Standard-Widgets (beim Init)
- `clock` — Uhr (client-side, immer aktiv)

## Eingerichtete Buttons
*(Werden vom Agent nach Bedarf hinzugefügt)*

## Notizen
- Server MUSS nach Tablet-Neustart manuell gestartet werden (via Heartbeat `ensure-running`)
- NIEMALS `> /dev/null` verwenden — wird von Safety Guard blockiert → immer `> ~/dashboard.log`
- Dashboard-Link IMMER in die Morgen-Nachricht einbauen

---
name: adguardhome
description: "AdGuardHome DNS-Server verwalten via Python-Tool. Sicher, blockiert NIE."
---

# AdGuardHome Skill

## Installations-Realitaet (Termux)

- Binary: `~/AdGuardHome/AdGuardHome`
- Version: `v0.107.72`
- Config: `~/AdGuardHome/AdGuardHome.yaml` (root-owned)
- Aktive Ports: DNS `53` (tcp/udp), Web-UI `8080`, Setup/Service `3000` kann zusaetzlich aktiv sein

## Workflow (VERBINDLICH)

1. Immer zuerst `status` ausfuehren
2. Dann exakt **einen** zielgerichteten Befehl ausfuehren
3. Danach erneut `status` oder passenden Read-Befehl zur Verifikation
4. Bei Konfig-Aenderungen: `restart` und Ergebnis verifizieren

Keine ad-hoc shell/python Konstrukte bauen, solange dieses Skill-Script den Use-Case abdeckt.

## EINZIGES Werkzeug: adguard-ctl.py

**ALLE** AdGuardHome-Aktionen laufen ueber das Python-Tool.
Keine rohen su/shell-Befehle! Das Tool garantiert Rueckkehr in max. 15s.

Pfad: `skills/adguardhome/scripts/adguard-ctl.py`

## Befehle

### Prozess-Verwaltung
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py status"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py start"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py stop"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py restart"})
```

### Konfiguration anzeigen
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py config"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py config dns"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py config filtering"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py config tls"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py rewrites"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py blocks"})
```

### DNS-Rewrites
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py rewrite-add beispiel.home 192.168.2.100"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py rewrite-del beispiel.home"})
```

### Dienste blockieren/entblocken
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py block facebook"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py unblock facebook"})
```

### Whitelist
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py whitelist-add example.com"})
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py whitelist-del example.com"})
```

### Upstream-DNS aendern
```bash
exec({"command": "python3 skills/adguardhome/scripts/adguard-ctl.py upstream https://dns.quad9.net/dns-query https://dns.google/dns-query"})
```

## VERBOTEN

- `su -c '...'` direkt fuer AdGuardHome ausfuehren
- `nohup`, `&`, `setsid` oder aehnliches manuell nutzen
- Shell-Befehle wie `pkill -f AdGuardHome`
- Config-Datei direkt mit `sed` bearbeiten

**IMMER** das Python-Tool verwenden. Es handhabt su, Timeouts, und
Daemon-Verwaltung intern und sicher.

## Info
- Web-UI: http://192.168.2.50:8080
- DNS: Port 53 (root noetig, Tool handhabt das)
- Config: ~/AdGuardHome/AdGuardHome.yaml (root-owned, Tool kann lesen/schreiben)
- Zentrale YAML-Bereiche: `dns`, `filtering`, `user_rules`, `blocked_services`, `rewrites`, `upstream_dns`

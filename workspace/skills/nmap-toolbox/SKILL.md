---
name: nmap-toolbox
description: Zuverlässige Netzwerk-Scans mit nmap. Verwende diesen Skill für: (1) LAN-Geräte finden (ping/network scan), (2) Port-Scans (offene Ports finden), (3) Service-Erkennung (welcher Dienst läuft), (4) OS-Detection, (5) aggressive Full-Scans. Immer timeout und max-retries setzen für Stabilität.
---

# nmap-toolbox

Schneller Zugriff auf alle nmap-Scans über das Python-Script.

## Script

```
skills/nmap-toolbox/scripts/nmap-toolbox.py
```

## Verfügbare Scans

| Scan | Befehl | Beschreibung |
|------|--------|--------------|
| `ping` | `python3 ... ping <IP>` | Ping-Scan, findet aktive Hosts |
| `network` | `python3 ... network <Subnetz>` | Netzwerk-Scan (z.B. 192.168.2.0/24) |
| `ports` | `python3 ... ports <IP> --ports 1-1000` | Port-Scan (TCP) |
| `top` | `python3 ... top <IP> --top 100` | Top-n häufigste Ports |
| `service` | `python3 ... service <IP>` | Dienst+Version erkennen |
| `os` | `python3 ... os <IP>` | OS-Detection |
| `aggressive` | `python3 ... aggressive <IP>` | Alles: OS, Service, Scripts, Traceroute |
| `tcp-full` | `python3 ... tcp-full <IP>` | Alle 65535 TCP-Ports |
| `udp-top` | `python3 ... udp-top <IP> --top 100` | Top UDP-Ports |

## Beispiele

```bash
# Netzwerk-Scan (alle Geräte im LAN)
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py network 192.168.2.0/24

# Einzelner Host - Ping
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py ping 192.168.2.1

# Port-Scan (alle gängigen Ports)
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py ports 192.168.2.1

# Top 100 Ports
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py top 192.168.2.1 --top 100

# Service-Erkennung
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py service 192.168.2.1

# Aggressive Scan (vollständig)
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py aggressive 192.168.2.1

# JSON-Output für Weiterverarbeitung
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py ports 192.168.2.1 --json

# Timeout erhöhen bei langsamen Targets
python3 skills/nmap-toolbox/scripts/nmap-toolbox.py service 192.168.2.1 --timeout 300
```

## Wichtig

- **Immer Timeout setzen**: `--timeout <sekunden>` (Standard: 120s)
- **Max-Retries**: Script setzt bereits `--max-retries 2`
- **Timing**: `-T3` für Balance Geschwindigkeit/Zuverlässigkeit
- **Output**: `--json` für strukturierte Ausgabe

## Typische Workflows

1. **LAN-Geräte finden**: `network 192.168.2.0/24` → MACs + IPs
2. **Bestimmtes Gerät scannen**: `ping <IP>` → Status prüfen
3. **Offene Ports finden**: `ports <IP>` oder `top <IP>`
4. **Dienst erkennen**: `service <IP>` → Port + Version
5. **Vollständig**: `aggressive <IP>`
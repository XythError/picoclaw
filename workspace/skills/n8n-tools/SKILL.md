---
name: n8n-tools
description: |
  n8n Workflow-Automatisierung (MCP + REST API + Webhooks).
  Nur verwenden wenn der Benutzer explizit nach n8n, Workflow-Automatisierung
  oder Workflow-Ausfuehrung fragt. Nicht fuer andere Aufgaben laden.
  Kann: Workflows suchen, ausfuehren, erstellen, verwalten, aktivieren/deaktivieren.
  Drei Kanaele: MCP (ausfuehren), REST API (verwalten), Webhooks (direkte Tool-Aufrufe).
---

# n8n Toolbox — MCP + REST API + Webhooks

Umfassende Anbindung an die selbstgehostete n8n-Instanz (`https://n8n.mytablab.de`).
Kombiniert drei Zugangskanaele intelligent:

| Kanal | Zweck | Authentifizierung |
|-------|-------|-------------------|
| **MCP** | Workflows suchen, inspizieren, ausfuehren | MCP Access Token |
| **REST API** | Workflows erstellen, verwalten, aktivieren | API Key |
| **Webhooks** | Registrierte Tools direkt aufrufen | Kein Auth noetig |

## Wann welchen Kanal verwenden

- **MCP** bevorzugen fuer: Workflow-Suche, Workflow-Ausfuehrung, Workflow-Details abrufen
- **REST API** verwenden fuer: Workflow erstellen, aktivieren/deaktivieren, Ausfuehrungshistorie
- **Webhooks** verwenden fuer: Bereits registrierte Tools schnell aufrufen

## Wichtig

- **MCP kann keine Workflows erstellen** — nur suchen und ausfuehren
- Fuer MCP muessen Workflows in n8n explizit freigeschaltet sein (Settings → Instance-level MCP)
- Alle Befehle geben **JSON** zurueck — Fehler enthalten ein `"error"` Feld
- Bei Verbindungsproblemen zuerst `test` ausfuehren fuer Diagnose

## Befehle

### MCP-Befehle (Suchen + Ausfuehren)

```bash
# MCP-Verbindung und verfuegbare Tools testen
python3 skills/n8n-tools/scripts/n8n.py mcp-init

# MCP-Tools auflisten (search_workflows, get_workflow_details, execute_workflow)
python3 skills/n8n-tools/scripts/n8n.py mcp-tools

# Workflows suchen (nach Name/Beschreibung)
python3 skills/n8n-tools/scripts/n8n.py mcp-search "social media"
python3 skills/n8n-tools/scripts/n8n.py mcp-search --limit 5

# Workflow-Details abrufen (Trigger, Nodes, Connections)
python3 skills/n8n-tools/scripts/n8n.py mcp-details <workflow-id>

# Workflow ausfuehren (verschiedene Input-Typen)
python3 skills/n8n-tools/scripts/n8n.py mcp-execute <workflow-id> '{"type":"webhook","webhookData":{"body":{"key":"value"}}}'
python3 skills/n8n-tools/scripts/n8n.py mcp-execute <workflow-id> '{"type":"chat","chatInput":"Hallo n8n"}'
python3 skills/n8n-tools/scripts/n8n.py mcp-execute <workflow-id> '{"type":"form","formData":{"field1":"wert1"}}'
```

### REST API-Befehle (Verwalten)

```bash
# Alle Workflows auflisten
python3 skills/n8n-tools/scripts/n8n.py workflows

# Workflow-Details (REST API)
python3 skills/n8n-tools/scripts/n8n.py workflow-info <id>

# Neuen Webhook-Workflow erstellen + automatisch registrieren
python3 skills/n8n-tools/scripts/n8n.py create-tool <name> "Beschreibung des Tools"

# Workflow aktivieren/deaktivieren
python3 skills/n8n-tools/scripts/n8n.py activate <id>
python3 skills/n8n-tools/scripts/n8n.py deactivate <id>

# Letzte Ausfuehrungen anzeigen
python3 skills/n8n-tools/scripts/n8n.py executions
python3 skills/n8n-tools/scripts/n8n.py executions --limit 20
```

### Webhook-Registry-Befehle (Lokale Tools)

```bash
# Registrierte Tools anzeigen
python3 skills/n8n-tools/scripts/n8n.py list

# Tool aufrufen
python3 skills/n8n-tools/scripts/n8n.py call <name> '{"param1":"wert1"}'

# Tool registrieren
python3 skills/n8n-tools/scripts/n8n.py register <name> <webhook-pfad> "Beschreibung"

# Tool entfernen
python3 skills/n8n-tools/scripts/n8n.py unregister <name>

# Webhook-Workflows automatisch entdecken
python3 skills/n8n-tools/scripts/n8n.py discover
```

### Diagnose-Befehle

```bash
# Vollstaendiger Verbindungstest (API + MCP + Webhook)
python3 skills/n8n-tools/scripts/n8n.py test

# Gesamtstatus (Verbindung, Workflows, Registry, MCP)
python3 skills/n8n-tools/scripts/n8n.py status
```

## Befehls-Uebersicht

| Befehl | Kanal | Beschreibung |
|--------|-------|--------------|
| mcp-init | MCP | MCP-Handshake testen |
| mcp-tools | MCP | Verfuegbare MCP-Tools auflisten |
| mcp-search | MCP | Workflows nach Name/Beschreibung suchen |
| mcp-details | MCP | Workflow-Details (Trigger, Nodes) abrufen |
| mcp-execute | MCP | Workflow ausfuehren (webhook/chat/form Input) |
| workflows | API | Alle Workflows auflisten |
| workflow-info | API | Workflow-Details (REST) |
| create-tool | API | Neuen Webhook-Workflow erstellen |
| activate | API | Workflow aktivieren |
| deactivate | API | Workflow deaktivieren |
| executions | API | Ausfuehrungshistorie |
| list | Lokal | Registrierte Tools anzeigen |
| call | Webhook | Registriertes Tool aufrufen |
| register | Lokal | Tool in Registry eintragen |
| unregister | Lokal | Tool aus Registry entfernen |
| discover | API | Webhook-Workflows automatisch finden |
| test | Alle | Verbindungstest (API + MCP + Webhook) |
| status | Alle | Gesamtstatus anzeigen |

## Typische Workflows

### Workflow suchen und ausfuehren (MCP)
1. `mcp-search "suchbegriff"` → Workflows finden
2. `mcp-details <id>` → Trigger-Typ und erwartete Inputs pruefen
3. `mcp-execute <id> '{"type":"webhook","webhookData":{"body":{...}}}'` → Ausfuehren

### Neues Tool erstellen (API + Webhook)
1. `create-tool wetter-check "Wetter fuer eine Stadt abfragen"` → Erstellt Webhook-Workflow
2. In n8n-Editor (`https://n8n.mytablab.de`) den 'Process'-Node anpassen
3. `call wetter-check '{"city":"Berlin"}'` → Tool verwenden

### Bestehende Workflows entdecken und registrieren
1. `discover` → Vorhandene Webhook-Workflows finden
2. `register <name> <webhook-pfad> "Beschreibung"` → Als Tool registrieren
3. `call <name> '{...}'` → Sofort verwendbar

### Sich selbst erweitern
PicoClaw kann neue Tools zur Laufzeit erstellen:
1. `create-tool` → Webhook-Workflow-Geruest in n8n erstellen
2. Benutzer oder PicoClaw passt Workflow-Logik im n8n-Editor an
3. Tool ist sofort ueber `call` verwendbar

## Konfiguration

| Parameter | Wert | Env-Variable |
|-----------|------|--------------|
| n8n URL | `https://n8n.mytablab.de` | `N8N_URL` |
| REST API Key | Aus Env/Secret-Datei laden (audience: public-api) | `N8N_API_KEY` |
| MCP Token | Aus Env/Secret-Datei laden (audience: mcp-server-api) | `N8N_MCP_TOKEN` |
| Registry | `tools.json` im Skill-Verzeichnis | — |
| MCP Endpoint | `https://n8n.mytablab.de/mcp-server/http` | — |

Optional kann eine Secret-Datei verwendet werden:
- `PICOCLAW_SECRETS_FILE` (Default: `~/.picoclaw/secrets.json`)
- Keys: `N8N_API_KEY`, `N8N_MCP_TOKEN`

## Fehlerbehandlung

- **Max. 3 Wiederholungen** bei HTTP-Fehlern (mit 2s Pause)
- **60s Timeout** fuer HTTP-Requests, **300s** fuer MCP-Ausfuehrungen
- **MCP SSE-Parsing**: Antworten kommen als `event: message\ndata: {json}` — wird automatisch geparst
- Bei Verbindungsproblemen: `test`-Befehl zeigt detaillierten Diagnose-Status
- Alle Befehle geben **JSON** zurueck — Fehler enthalten `"error"` Feld

## Einschraenkungen

- **MCP kann keine Workflows erstellen** — nur suchen und ausfuehren (REST API verwenden)
- **Workflows muessen fuer MCP freigegeben sein** (n8n Settings → Instance-level MCP)
- **MCP Timeout: 5 Minuten** (hart kodiert in n8n, nicht aenderbar)
- **Nur Text-Input** ueber MCP (kein Binary/Datei-Upload)
- `create-tool` erstellt ein Geruest — echte Logik muss im n8n-Editor ergaenzt werden
- Webhook-Workflows muessen **aktiv** sein um Aufrufe zu empfangen
- n8n muss vom Netzwerk des Tablets aus erreichbar sein

## Ausgabe

Alle Befehle geben JSON zurueck. Beispiele:

```json
// Erfolg
{"workflow_count": 2, "workflows": [...]}

// Fehler
{"error": "MCP request failed (HTTP 401)", "hint": "MCP Token pruefen"}

// MCP-Ausfuehrung
{"workflow_id": "abc123", "result": {"data": [...], "count": 1}}
```

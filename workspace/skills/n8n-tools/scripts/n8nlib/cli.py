#!/usr/bin/env python3
"""
PicoClaw n8n Toolbox — MCP + REST API + Webhooks

Umfassende Anbindung an selbstgehostete n8n-Instanz.
Kombiniert drei Zugangskanaele intelligent:

  MCP Protocol:  Workflows suchen, inspizieren, ausfuehren (read + execute)
  REST API:      Workflows erstellen, verwalten, aktivieren (write + manage)
  Webhooks:      Registrierte Tools direkt aufrufen (direct call)

MCP-Protokoll:
  - JSON-RPC 2.0 ueber HTTP POST
  - Antworten im SSE-Format (event: message / data: {json})
  - Stateless (kein Session-Management noetig)
  - 3 Meta-Tools: search_workflows, get_workflow_details, execute_workflow

Voraussetzungen: Python 3, curl (in Termux verfuegbar)
"""

import json
import sys
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent.parent
REGISTRY_FILE = SKILL_DIR / "tools.json"


def _load_secret(name: str, default: str = "") -> str:
    """Load secret from env first, then optional secrets file."""
    value = os.environ.get(name)
    if value:
        return value

    secret_file = Path(
        os.environ.get(
            "PICOCLAW_SECRETS_FILE",
            str(Path.home() / ".picoclaw" / "secrets.json"),
        )
    )
    try:
        if secret_file.exists():
            data = json.loads(secret_file.read_text(encoding="utf-8"))
            value = data.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception:
        pass

    return default

# n8n connection
N8N_URL = os.environ.get("N8N_URL", "https://n8n.mytablab.de")

# REST API Key (audience: public-api)
N8N_API_KEY = _load_secret("N8N_API_KEY")

# MCP Access Token (audience: mcp-server-api)
N8N_MCP_TOKEN = _load_secret("N8N_MCP_TOKEN")

# MCP endpoint
N8N_MCP_URL = f"{N8N_URL}/mcp-server/http"

# SSL cert for Termux
SSL_CERT = "/data/data/com.termux/files/usr/etc/tls/cert.pem"

# Retry config
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
HTTP_TIMEOUT = 60  # seconds
MCP_EXECUTE_TIMEOUT = 300  # 5 minutes (n8n MCP hard limit)

# JSON-RPC request ID counter
_request_id = 0


def _next_id() -> int:
    """Generate next JSON-RPC request ID."""
    global _request_id
    _request_id += 1
    return _request_id


# ═══════════════════════════════════════════════════════════════════════
# HTTP Client (curl-basiert, zuverlaessig in Termux)
# ═══════════════════════════════════════════════════════════════════════

def http_request(url: str, method: str = "GET", data: Any = None,
                 headers: dict = None, timeout: int = None,
                 accept: str = "application/json",
                 raw_response: bool = False) -> dict:
    """HTTP-Request via curl ausfuehren.

    Args:
        url: Ziel-URL
        method: HTTP-Methode (GET, POST, PUT, DELETE, PATCH)
        data: Request-Body (wird als JSON serialisiert)
        headers: Zusaetzliche HTTP-Header
        timeout: Timeout in Sekunden (Standard: HTTP_TIMEOUT)
        accept: Accept-Header (Standard: application/json)
        raw_response: Wenn True, Body nicht als JSON parsen

    Returns:
        {"status": int, "data": dict|str, "raw": str (nur bei raw_response)}
    """
    if timeout is None:
        timeout = HTTP_TIMEOUT

    cmd = ["curl", "-s", "-S", "--max-time", str(timeout)]

    # SSL cert
    if os.path.exists(SSL_CERT):
        cmd += ["--cacert", SSL_CERT]
    else:
        cmd += ["-k"]  # fallback: skip verify

    # Method
    if method != "GET":
        cmd += ["-X", method]

    # Headers
    cmd += ["-H", "Content-Type: application/json"]
    cmd += ["-H", f"Accept: {accept}"]
    if headers:
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]

    # Body
    if data is not None:
        body_str = json.dumps(data, ensure_ascii=False)
        cmd += ["-d", body_str]

    # Status code extraction
    cmd += ["-w", "\n__HTTP_CODE__%{http_code}"]
    cmd += [url]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout + 10)
        output = r.stdout

        # Split body and status code
        if "__HTTP_CODE__" in output:
            parts = output.rsplit("__HTTP_CODE__", 1)
            body = parts[0].strip()
            code = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
        else:
            body = output.strip()
            code = 0

        # Raw response mode (for SSE)
        if raw_response:
            return {"status": code, "data": body, "raw": body}

        # Parse JSON body
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw_response": body}

        return {"status": code, "data": parsed}

    except subprocess.TimeoutExpired:
        return {"status": 0, "data": {"error": f"Request timeout nach {timeout}s"}}
    except Exception as e:
        return {"status": 0, "data": {"error": str(e)}}


def http_request_with_retry(url: str, method: str = "GET", data: Any = None,
                            headers: dict = None, timeout: int = None,
                            accept: str = "application/json",
                            raw_response: bool = False,
                            max_retries: int = None) -> dict:
    """HTTP-Request mit automatischen Wiederholungen bei Fehlern.

    Wiederholt bei: Timeout, HTTP 5xx, Verbindungsfehler.
    Nicht wiederholt bei: HTTP 4xx (Client-Fehler).
    """
    if max_retries is None:
        max_retries = MAX_RETRIES

    last_result = None
    for attempt in range(max_retries):
        result = http_request(url, method, data, headers, timeout,
                              accept, raw_response)
        last_result = result

        status = result.get("status", 0)

        # Erfolg oder Client-Fehler → nicht wiederholen
        if 200 <= status < 300:
            return result
        if 400 <= status < 500:
            return result  # Client-Fehler, Retry sinnlos

        # Server-Fehler oder Timeout → wiederholen
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY * (attempt + 1))  # exponential backoff

    return last_result


# ═══════════════════════════════════════════════════════════════════════
# MCP Client (JSON-RPC 2.0 ueber HTTP, SSE-Antworten)
# ═══════════════════════════════════════════════════════════════════════

def mcp_request(method: str, params: dict = None,
                is_notification: bool = False,
                timeout: int = None) -> dict:
    """MCP JSON-RPC 2.0 Request an n8n senden.

    Args:
        method: JSON-RPC Methode (z.B. "initialize", "tools/list", "tools/call")
        params: Parameter-Objekt
        is_notification: Wenn True, keine Response erwartet (keine ID)
        timeout: Request-Timeout (Standard: HTTP_TIMEOUT)

    Returns:
        {"success": bool, "result": dict|None, "error": dict|None}
    """
    if timeout is None:
        timeout = HTTP_TIMEOUT

    if not N8N_MCP_TOKEN:
        return {
            "success": False,
            "result": None,
            "error": {
                "code": "missing_mcp_token",
                "message": "N8N_MCP_TOKEN fehlt (env oder PICOCLAW_SECRETS_FILE)",
            },
        }

    # JSON-RPC 2.0 Request bauen
    request = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if params:
        request["params"] = params
    if not is_notification:
        request["id"] = _next_id()

    # HTTP POST zum MCP-Endpoint
    result = http_request_with_retry(
        url=N8N_MCP_URL,
        method="POST",
        data=request,
        headers={"Authorization": f"Bearer {N8N_MCP_TOKEN}"},
        timeout=timeout,
        accept="application/json, text/event-stream",
        raw_response=True,  # SSE-Format parsen
    )

    status = result.get("status", 0)
    raw_body = result.get("raw", "")

    # HTTP-Fehler
    if status < 200 or status >= 300:
        error_detail = raw_body[:500] if raw_body else f"HTTP {status}"
        return {
            "success": False,
            "result": None,
            "error": {
                "code": status,
                "message": f"MCP HTTP-Fehler: {status}",
                "detail": error_detail,
            },
        }

    # Notification → keine Antwort erwartet
    if is_notification:
        return {"success": True, "result": None, "error": None}

    # SSE-Format parsen: "event: message\ndata: {json}\n\n"
    jsonrpc_response = _parse_sse_response(raw_body)

    if jsonrpc_response is None:
        return {
            "success": False,
            "result": None,
            "error": {
                "code": -1,
                "message": "Konnte SSE-Antwort nicht parsen",
                "detail": raw_body[:500],
            },
        }

    # JSON-RPC Fehler pruefen
    if "error" in jsonrpc_response:
        return {
            "success": False,
            "result": None,
            "error": jsonrpc_response["error"],
        }

    # Erfolg
    return {
        "success": True,
        "result": jsonrpc_response.get("result"),
        "error": None,
    }


def _parse_sse_response(body: str) -> Optional[dict]:
    """SSE-Antwort parsen und JSON-RPC Response extrahieren.

    n8n MCP Server antwortet im Format:
        event: message
        data: {"result":{...},"jsonrpc":"2.0","id":N}

    Oder manchmal als reines JSON (Fallback).
    """
    if not body:
        return None

    # Methode 1: SSE-Format — "data:" Zeile finden
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            json_str = line[6:]  # "data: " = 6 Zeichen
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
        elif line.startswith("data:"):
            json_str = line[5:]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue

    # Methode 2: Reines JSON (kein SSE-Wrapper)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass

    return None


def mcp_initialize() -> dict:
    """MCP-Handshake durchfuehren (initialize + initialized notification).

    Returns:
        Initialize-Result mit Server-Info und Capabilities.
    """
    # Schritt 1: Initialize Request
    result = mcp_request("initialize", params={
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {
            "name": "picoclaw",
            "version": "1.0.0",
        },
    })

    if not result["success"]:
        return {"error": "MCP Initialize fehlgeschlagen",
                "details": result["error"]}

    server_info = result["result"]

    # Schritt 2: Initialized Notification (kein Response erwartet)
    mcp_request("notifications/initialized", is_notification=True)

    return {
        "initialized": True,
        "server": server_info.get("serverInfo", {}),
        "protocol_version": server_info.get("protocolVersion", ""),
        "capabilities": server_info.get("capabilities", {}),
    }


def mcp_list_tools() -> dict:
    """MCP-Tools auflisten (tools/list).

    Returns:
        Liste der verfuegbaren MCP-Tools mit Schemas.
    """
    result = mcp_request("tools/list", params={})

    if not result["success"]:
        return {"error": "MCP tools/list fehlgeschlagen",
                "details": result["error"]}

    tools = result["result"].get("tools", [])
    return {
        "tool_count": len(tools),
        "tools": [
            {
                "name": t.get("name", ""),
                "description": t.get("description", "")[:200],
                "parameters": list(
                    t.get("inputSchema", {}).get("properties", {}).keys()
                ),
            }
            for t in tools
        ],
    }


def mcp_call_tool(tool_name: str, arguments: dict = None,
                  timeout: int = None) -> dict:
    """MCP-Tool aufrufen (tools/call).

    Args:
        tool_name: Name des MCP-Tools (search_workflows, get_workflow_details, execute_workflow)
        arguments: Tool-Argumente als Dict
        timeout: Timeout in Sekunden

    Returns:
        Tool-Ergebnis oder Fehler.
    """
    result = mcp_request("tools/call", params={
        "name": tool_name,
        "arguments": arguments or {},
    }, timeout=timeout or HTTP_TIMEOUT)

    if not result["success"]:
        return {"error": f"MCP {tool_name} fehlgeschlagen",
                "details": result["error"]}

    # MCP tools/call Ergebnis extrahieren
    mcp_result = result["result"]

    # content[] Array verarbeiten — Text-Content extrahieren
    content = mcp_result.get("content", [])
    text_parts = []
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            # Versuche JSON zu parsen
            try:
                text_parts.append(json.loads(text))
            except json.JSONDecodeError:
                text_parts.append(text)

    # structuredContent hat Prioritaet
    structured = mcp_result.get("structuredContent")
    if structured:
        return {"result": structured}

    if len(text_parts) == 1:
        return {"result": text_parts[0]}
    elif text_parts:
        return {"result": text_parts}
    else:
        return {"result": mcp_result}


# ═══════════════════════════════════════════════════════════════════════
# REST API Client
# ═══════════════════════════════════════════════════════════════════════

def n8n_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """n8n REST API mit Authentifizierung aufrufen."""
    if not N8N_API_KEY:
        return {
            "status": 0,
            "data": {
                "error": {
                    "code": "missing_api_key",
                    "message": "N8N_API_KEY fehlt (env oder PICOCLAW_SECRETS_FILE)",
                }
            },
        }

    url = f"{N8N_URL}/api/v1/{endpoint.lstrip('/')}"
    return http_request_with_retry(
        url, method=method, data=data,
        headers={"X-N8N-API-KEY": N8N_API_KEY}
    )


def n8n_webhook(path: str, data: dict = None, method: str = "POST") -> dict:
    """n8n Webhook-Endpoint aufrufen."""
    url = f"{N8N_URL}/webhook/{path.lstrip('/')}"
    return http_request_with_retry(url, method=method, data=data)


# ═══════════════════════════════════════════════════════════════════════
# Tool Registry (tools.json)
# ═══════════════════════════════════════════════════════════════════════

def load_registry() -> dict:
    """Tool-Registry aus tools.json laden."""
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"tools": {}, "meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%S")}}


def save_registry(registry: dict):
    """Tool-Registry in tools.json speichern."""
    registry.setdefault("meta", {})
    registry["meta"]["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════
# MCP-Befehle
# ═══════════════════════════════════════════════════════════════════════

def cmd_mcp_init() -> dict:
    """MCP-Verbindung initialisieren und testen."""
    return mcp_initialize()


def cmd_mcp_tools() -> dict:
    """Verfuegbare MCP-Tools auflisten."""
    # Erst initialisieren, dann Tools listen
    init = mcp_initialize()
    if "error" in init:
        return init

    return mcp_list_tools()


def cmd_mcp_search(query: str = "", limit: int = 50) -> dict:
    """Workflows ueber MCP suchen.

    Args:
        query: Suchbegriff (Name/Beschreibung)
        limit: Maximale Anzahl Ergebnisse (Standard: 50, Max: 200)
    """
    # Initialisieren
    init = mcp_initialize()
    if "error" in init:
        return init

    # search_workflows aufrufen
    args = {}
    if query:
        args["query"] = query
    if limit:
        args["limit"] = min(limit, 200)

    return mcp_call_tool("search_workflows", args)


def cmd_mcp_details(workflow_id: str) -> dict:
    """Workflow-Details ueber MCP abrufen.

    Args:
        workflow_id: ID des Workflows
    """
    if not workflow_id:
        return {"error": "Workflow-ID erforderlich"}

    # Initialisieren
    init = mcp_initialize()
    if "error" in init:
        return init

    return mcp_call_tool("get_workflow_details", {"workflowId": workflow_id})


def cmd_mcp_execute(workflow_id: str, inputs: dict = None) -> dict:
    """Workflow ueber MCP ausfuehren.

    Args:
        workflow_id: ID des Workflows
        inputs: Input-Daten, Format abhaengig vom Trigger-Typ:
            - {"type": "webhook", "webhookData": {"body": {...}, "method": "POST"}}
            - {"type": "chat", "chatInput": "Nachricht"}
            - {"type": "form", "formData": {"feld": "wert"}}
            - Wenn None/leer: Workflow ohne spezifische Inputs ausfuehren

    Returns:
        Workflow-Ergebnis oder Fehler.
    """
    if not workflow_id:
        return {"error": "Workflow-ID erforderlich"}

    # Initialisieren
    init = mcp_initialize()
    if "error" in init:
        return init

    # execute_workflow aufrufen
    args = {"workflowId": workflow_id}
    if inputs:
        args["inputs"] = inputs

    result = mcp_call_tool("execute_workflow", args,
                           timeout=MCP_EXECUTE_TIMEOUT)

    if "error" not in result:
        result["workflow_id"] = workflow_id

    return result


# ═══════════════════════════════════════════════════════════════════════
# REST API-Befehle
# ═══════════════════════════════════════════════════════════════════════

def cmd_workflows() -> dict:
    """Alle n8n-Workflows ueber REST API auflisten."""
    result = n8n_api("workflows?limit=100")

    if result["status"] != 200:
        return {"error": f"API-Fehler (HTTP {result['status']})",
                "details": result["data"]}

    workflows = result["data"].get("data", result["data"])
    if isinstance(workflows, list):
        return {
            "workflow_count": len(workflows),
            "workflows": [
                {
                    "id": w.get("id"),
                    "name": w.get("name"),
                    "active": w.get("active", False),
                    "created": w.get("createdAt", ""),
                    "updated": w.get("updatedAt", ""),
                    "tags": [t.get("name", "") for t in w.get("tags", [])],
                }
                for w in workflows
            ],
        }
    return {"error": "Unerwartetes API-Antwortformat", "raw": workflows}


def cmd_workflow_info(workflow_id: str) -> dict:
    """Detaillierte Infos zu einem Workflow ueber REST API."""
    result = n8n_api(f"workflows/{workflow_id}")

    if result["status"] != 200:
        return {"error": f"API-Fehler (HTTP {result['status']})",
                "details": result["data"]}

    w = result["data"]
    nodes = w.get("nodes", [])

    # Webhook-Trigger finden
    webhooks = [n for n in nodes if "webhook" in n.get("type", "").lower()
                or "Webhook" in n.get("name", "")]

    return {
        "id": w.get("id"),
        "name": w.get("name"),
        "active": w.get("active", False),
        "node_count": len(nodes),
        "node_types": list(set(n.get("type", "") for n in nodes)),
        "webhooks": [
            {
                "name": wh.get("name"),
                "type": wh.get("type"),
                "path": wh.get("parameters", {}).get("path", ""),
                "method": wh.get("parameters", {}).get("httpMethod", "POST"),
            }
            for wh in webhooks
        ],
        "connections": list(w.get("connections", {}).keys()),
    }


def cmd_executions(limit: int = 10) -> dict:
    """Letzte Workflow-Ausfuehrungen auflisten."""
    result = n8n_api(f"executions?limit={limit}")

    if result["status"] != 200:
        return {"error": f"API-Fehler (HTTP {result['status']})",
                "details": result["data"]}

    execs = result["data"].get("data", result["data"])
    if isinstance(execs, list):
        return {
            "execution_count": len(execs),
            "executions": [
                {
                    "id": e.get("id"),
                    "workflow_id": e.get("workflowId") or
                                   e.get("workflowData", {}).get("id"),
                    "workflow_name": e.get("workflowData", {}).get("name", ""),
                    "status": e.get("status", ""),
                    "started": e.get("startedAt", ""),
                    "finished": e.get("stoppedAt", ""),
                    "mode": e.get("mode", ""),
                }
                for e in execs
            ],
        }
    return {"raw": execs}


def cmd_create_tool(name: str, description: str,
                    response_text: str = None) -> dict:
    """Neuen Webhook-Workflow in n8n erstellen und als Tool registrieren.

    Erstellt: Webhook → Code (Verarbeitung) → Respond to Webhook.
    Der Code-Node kann danach im n8n-Editor angepasst werden.
    """
    # Validierung
    if not name:
        return {"error": "Tool-Name erforderlich"}
    if not description:
        return {"error": "Beschreibung erforderlich"}
    if not all(c.isalnum() or c in ('-', '_') for c in name):
        return {"error": "Name: nur Buchstaben, Zahlen, Bindestrich, Unterstrich"}

    webhook_path = f"picoclaw/{name}"

    # Workflow-JSON bauen
    webhook_id = str(uuid.uuid4())
    node_ids = [str(uuid.uuid4()) for _ in range(3)]

    workflow = {
        "name": f"PicoClaw Tool: {name}",
        "nodes": [
            {
                "parameters": {
                    "path": webhook_path,
                    "httpMethod": "POST",
                    "responseMode": "responseNode",
                    "options": {},
                },
                "id": node_ids[0],
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2,
                "position": [260, 300],
                "webhookId": webhook_id,
            },
            {
                "parameters": {
                    "jsCode": (
                        f"// PicoClaw Tool: {name}\n"
                        "// Eingehenden Request von PicoClaw verarbeiten\n"
                        "// Input: items[0].json enthaelt den Webhook-Payload\n"
                        "// Diesen Code anpassen um Tool-Logik zu implementieren\n\n"
                        "const input = items[0].json;\n"
                        f"const toolName = input._meta?.tool || '{name}';\n\n"
                        "// TODO: Tool-Logik hier implementieren\n"
                        "// n8n-Nodes koennen durch Hinzufuegen zum Workflow genutzt werden\n\n"
                        "return [{\n"
                        "  json: {\n"
                        "    success: true,\n"
                        "    tool: toolName,\n"
                        "    message: " + json.dumps(
                            response_text or f"Tool '{name}' erfolgreich ausgefuehrt"
                        ) + ",\n"
                        "    input: input,\n"
                        "    timestamp: new Date().toISOString()\n"
                        "  }\n"
                        "}];\n"
                    ),
                },
                "id": node_ids[1],
                "name": "Process",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [480, 300],
            },
            {
                "parameters": {
                    "respondWith": "json",
                    "responseBody": "={{ JSON.stringify($json) }}",
                    "options": {},
                },
                "id": node_ids[2],
                "name": "Respond",
                "type": "n8n-nodes-base.respondToWebhook",
                "typeVersion": 1.1,
                "position": [700, 300],
            },
        ],
        "connections": {
            "Webhook": {
                "main": [[{"node": "Process", "type": "main", "index": 0}]]
            },
            "Process": {
                "main": [[{"node": "Respond", "type": "main", "index": 0}]]
            },
        },
        "settings": {"executionOrder": "v1"},
    }

    # Workflow via API erstellen
    result = n8n_api("workflows", method="POST", data=workflow)

    if result["status"] not in (200, 201):
        return {"error": f"Workflow-Erstellung fehlgeschlagen (HTTP {result['status']})",
                "details": result["data"]}

    workflow_id = result["data"].get("id", "")

    # Workflow aktivieren
    act = n8n_api(f"workflows/{workflow_id}/activate", method="POST")
    activated = act["status"] in (200, 201)

    # Im lokalen Registry registrieren
    reg = cmd_register(name, webhook_path, description,
                       workflow_id=workflow_id)

    return {
        "action": "erstellt",
        "tool": name,
        "workflow_id": workflow_id,
        "webhook_path": webhook_path,
        "webhook_url": f"{N8N_URL}/webhook/{webhook_path}",
        "activated": activated,
        "registered": reg.get("action") in ("registered", "registriert"),
        "hinweis": "Workflow erstellt und registriert. "
                   "'Process'-Node im n8n-Editor anpassen fuer echte Logik.",
    }


def cmd_activate(workflow_id: str) -> dict:
    """Workflow aktivieren."""
    result = n8n_api(f"workflows/{workflow_id}/activate", method="POST")
    return {
        "action": "aktiviert",
        "workflow_id": workflow_id,
        "success": result["status"] in (200, 201),
        "status": result["status"],
    }


def cmd_deactivate(workflow_id: str) -> dict:
    """Workflow deaktivieren."""
    result = n8n_api(f"workflows/{workflow_id}/deactivate", method="POST")
    return {
        "action": "deaktiviert",
        "workflow_id": workflow_id,
        "success": result["status"] in (200, 201),
        "status": result["status"],
    }


# ═══════════════════════════════════════════════════════════════════════
# Webhook-Registry-Befehle
# ═══════════════════════════════════════════════════════════════════════

def cmd_list() -> dict:
    """Alle registrierten Tools anzeigen."""
    reg = load_registry()
    tools = []
    for name, info in reg.get("tools", {}).items():
        tools.append({
            "name": name,
            "description": info.get("description", ""),
            "webhook": info.get("webhook", ""),
            "params": info.get("params", {}),
            "workflow_id": info.get("workflow_id", ""),
        })
    return {
        "registered_tools": len(tools),
        "tools": tools,
    }


def cmd_call(tool_name: str, params: dict = None) -> dict:
    """Registriertes Tool per Webhook aufrufen."""
    reg = load_registry()
    tools = reg.get("tools", {})

    if tool_name not in tools:
        return {
            "error": f"Tool '{tool_name}' nicht gefunden",
            "verfuegbar": list(tools.keys()),
            "hinweis": "'list' zeigt registrierte Tools, "
                       "'register' fuegt neue hinzu.",
        }

    tool = tools[tool_name]
    webhook_path = tool.get("webhook", "")

    if not webhook_path:
        return {"error": f"Tool '{tool_name}' hat keinen Webhook konfiguriert"}

    # Payload bauen
    payload = params or {}
    payload["_meta"] = {
        "tool": tool_name,
        "caller": "picoclaw",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Webhook aufrufen
    method = tool.get("method", "POST")
    result = n8n_webhook(webhook_path, data=payload, method=method)

    return {
        "tool": tool_name,
        "webhook": webhook_path,
        "http_status": result["status"],
        "response": result["data"],
    }


def cmd_register(name: str, webhook: str, description: str,
                 params: dict = None, workflow_id: str = "") -> dict:
    """Tool in der Registry registrieren."""
    if not name or not webhook:
        return {"error": "Name und Webhook-Pfad erforderlich"}

    if not all(c.isalnum() or c in ('-', '_') for c in name):
        return {"error": "Name: nur Buchstaben, Zahlen, Bindestrich, Unterstrich"}

    reg = load_registry()
    was_update = name in reg.get("tools", {})

    reg.setdefault("tools", {})[name] = {
        "description": description,
        "webhook": webhook,
        "params": params or {},
        "workflow_id": workflow_id,
        "registered": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    save_registry(reg)

    return {
        "action": "aktualisiert" if was_update else "registriert",
        "tool": name,
        "webhook": webhook,
        "description": description,
    }


def cmd_unregister(name: str) -> dict:
    """Tool aus der Registry entfernen."""
    reg = load_registry()

    if name not in reg.get("tools", {}):
        return {"error": f"Tool '{name}' nicht in Registry gefunden"}

    del reg["tools"][name]
    save_registry(reg)

    return {"action": "entfernt", "tool": name}


def cmd_discover() -> dict:
    """Webhook-Workflows in n8n automatisch entdecken."""
    result = n8n_api("workflows?limit=100")

    if result["status"] != 200:
        return {"error": f"API-Fehler (HTTP {result['status']})"}

    workflows = result["data"].get("data", result["data"])
    if not isinstance(workflows, list):
        return {"error": "Unerwartetes API-Antwortformat"}

    reg = load_registry()
    registered_ids = {t.get("workflow_id") for t in reg.get("tools", {}).values()}

    discovered = []
    for w in workflows:
        nodes = w.get("nodes", [])
        webhook_nodes = [
            n for n in nodes
            if "webhook" in n.get("type", "").lower()
            or n.get("type", "") == "n8n-nodes-base.formTrigger"
        ]

        if webhook_nodes:
            wh = webhook_nodes[0]
            path = wh.get("parameters", {}).get("path", "")

            discovered.append({
                "workflow_id": w.get("id"),
                "name": w.get("name"),
                "active": w.get("active", False),
                "webhook_path": path,
                "webhook_type": wh.get("type"),
                "bereits_registriert": w.get("id") in registered_ids,
            })

    return {
        "gefunden": len(discovered),
        "webhook_workflows": discovered,
        "hinweis": "'register <name> <webhook-pfad> \"Beschreibung\"' "
                   "zum Registrieren verwenden.",
    }


# ═══════════════════════════════════════════════════════════════════════
# Diagnose-Befehle
# ═══════════════════════════════════════════════════════════════════════

def cmd_test() -> dict:
    """Vollstaendiger Verbindungstest (API + MCP + Webhook)."""
    results = {
        "n8n_url": N8N_URL,
        "mcp_endpoint": N8N_MCP_URL,
    }

    # 1. REST API testen
    api_result = n8n_api("workflows?limit=1")
    results["api"] = {
        "erreichbar": api_result["status"] == 200,
        "status": api_result["status"],
    }

    # 2. MCP-Endpoint testen
    try:
        mcp_result = mcp_initialize()
        results["mcp"] = {
            "erreichbar": "error" not in mcp_result,
            "initialisiert": mcp_result.get("initialized", False),
            "server": mcp_result.get("server", {}),
        }
        if "error" in mcp_result:
            results["mcp"]["fehler"] = mcp_result["error"]
    except Exception as e:
        results["mcp"] = {"erreichbar": False, "fehler": str(e)}

    # 3. Webhook-Endpoint testen (404 = erreichbar, nur kein Route)
    wh_result = http_request(f"{N8N_URL}/webhook/health", method="GET")
    results["webhook"] = {
        "erreichbar": wh_result["status"] in (200, 404, 405),
        "status": wh_result["status"],
    }

    # 4. Registry-Status
    reg = load_registry()
    results["registry"] = {
        "datei": str(REGISTRY_FILE),
        "existiert": REGISTRY_FILE.exists(),
        "tools_anzahl": len(reg.get("tools", {})),
    }

    return results


def cmd_status() -> dict:
    """Gesamtstatus: Verbindung, Workflows, Registry, MCP."""
    status = {"n8n_url": N8N_URL}

    # Workflows zaehlen
    wf_result = n8n_api("workflows?limit=100")
    if wf_result["status"] == 200:
        workflows = wf_result["data"].get("data", [])
        if isinstance(workflows, list):
            active = sum(1 for w in workflows if w.get("active"))
            status["workflows"] = {
                "gesamt": len(workflows),
                "aktiv": active,
                "inaktiv": len(workflows) - active,
            }
        else:
            status["workflows"] = {"fehler": "Unerwartetes Format"}
    else:
        status["workflows"] = {"fehler": f"HTTP {wf_result['status']}"}

    # MCP-Status
    try:
        mcp_result = mcp_initialize()
        if "error" not in mcp_result:
            tools_result = mcp_list_tools()
            status["mcp"] = {
                "verbunden": True,
                "tools": tools_result.get("tool_count", 0),
            }
        else:
            status["mcp"] = {"verbunden": False,
                             "fehler": str(mcp_result.get("error", ""))}
    except Exception as e:
        status["mcp"] = {"verbunden": False, "fehler": str(e)}

    # Registry
    reg = load_registry()
    tools = reg.get("tools", {})
    status["registry"] = {
        "tools_anzahl": len(tools),
        "tools": list(tools.keys()) if tools else [],
    }

    return status


# ═══════════════════════════════════════════════════════════════════════
# CLI Parser
# ═══════════════════════════════════════════════════════════════════════

def parse_json_arg(arg: str) -> dict:
    """JSON-Argument parsen (String oder Dateipfad)."""
    if not arg:
        return {}
    # Als JSON-String versuchen
    try:
        return json.loads(arg)
    except json.JSONDecodeError:
        pass
    # Als Dateipfad versuchen
    p = Path(arg)
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"error": f"Konnte JSON nicht parsen: {arg}"}


COMMANDS = {
    # MCP
    "mcp-init":     ("MCP-Verbindung testen",                          "MCP"),
    "mcp-tools":    ("Verfuegbare MCP-Tools auflisten",                "MCP"),
    "mcp-search":   ("Workflows suchen: mcp-search [query] [--limit N]", "MCP"),
    "mcp-details":  ("Workflow-Details: mcp-details <id>",              "MCP"),
    "mcp-execute":  ("Workflow ausfuehren: mcp-execute <id> [inputs-json]", "MCP"),
    # REST API
    "workflows":    ("Alle Workflows auflisten",                       "API"),
    "workflow-info":("Workflow-Details: workflow-info <id>",            "API"),
    "create-tool":  ("Webhook-Workflow erstellen: create-tool <name> <desc>", "API"),
    "activate":     ("Workflow aktivieren: activate <id>",              "API"),
    "deactivate":   ("Workflow deaktivieren: deactivate <id>",         "API"),
    "executions":   ("Letzte Ausfuehrungen: executions [--limit N]",   "API"),
    # Registry
    "list":         ("Registrierte Tools anzeigen",                    "Lokal"),
    "call":         ("Tool aufrufen: call <name> [json-params]",       "Webhook"),
    "register":     ("Tool registrieren: register <name> <webhook> <desc>", "Lokal"),
    "unregister":   ("Tool entfernen: unregister <name>",              "Lokal"),
    "discover":     ("Webhook-Workflows entdecken",                    "API"),
    # Diagnose
    "test":         ("Verbindungstest (API + MCP + Webhook)",          "Alle"),
    "status":       ("Gesamtstatus anzeigen",                          "Alle"),
}


def print_help():
    """Hilfe-Text ausgeben."""
    print("PicoClaw n8n Toolbox — MCP + REST API + Webhooks")
    print(f"Verwendung: {sys.argv[0]} <befehl> [argumente...]")
    print(f"\nn8n URL:      {N8N_URL}")
    print(f"MCP Endpoint: {N8N_MCP_URL}")
    print(f"Registry:     {REGISTRY_FILE}")
    print()

    # Nach Kanal gruppiert
    categories = {}
    for name, (desc, cat) in COMMANDS.items():
        categories.setdefault(cat, []).append((name, desc))

    for cat in ["MCP", "API", "Webhook", "Lokal", "Alle"]:
        if cat in categories:
            print(f"  [{cat}]")
            for name, desc in categories[cat]:
                print(f"    {name:16s} {desc}")
            print()


def _has_error(result: Any) -> bool:
    if isinstance(result, dict):
        if result.get("success") is False:
            return True
        if "error" in result and result.get("error"):
            return True
        details = result.get("details")
        if isinstance(details, dict) and details.get("error"):
            return True
    return False


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]
    result = None

    # ─── MCP-Befehle ────────────────────────────────────────

    if cmd == "mcp-init":
        result = cmd_mcp_init()

    elif cmd == "mcp-tools":
        result = cmd_mcp_tools()

    elif cmd == "mcp-search":
        query = ""
        limit = 50
        i = 0
        while i < len(args):
            if args[i] == "--limit" and i + 1 < len(args):
                limit = int(args[i + 1])
                i += 2
            elif args[i].isdigit() and not query:
                limit = int(args[i])
                i += 1
            else:
                query = args[i]
                i += 1
        result = cmd_mcp_search(query, limit)

    elif cmd == "mcp-details":
        if not args:
            result = {"error": "Verwendung: mcp-details <workflow-id>"}
        else:
            result = cmd_mcp_details(args[0])

    elif cmd == "mcp-execute":
        if not args:
            result = {"error": "Verwendung: mcp-execute <workflow-id> [inputs-json]"}
        else:
            inputs = parse_json_arg(args[1]) if len(args) > 1 else None
            if inputs and "error" in inputs:
                result = inputs
            else:
                result = cmd_mcp_execute(args[0], inputs)

    # ─── REST API-Befehle ───────────────────────────────────

    elif cmd == "workflows":
        result = cmd_workflows()

    elif cmd == "workflow-info":
        if not args:
            result = {"error": "Verwendung: workflow-info <workflow-id>"}
        else:
            result = cmd_workflow_info(args[0])

    elif cmd == "executions":
        limit = 10
        if args and args[0] == "--limit" and len(args) > 1:
            limit = int(args[1])
        elif args and args[0].isdigit():
            limit = int(args[0])
        result = cmd_executions(limit)

    elif cmd == "create-tool":
        if len(args) < 2:
            result = {"error": "Verwendung: create-tool <name> <beschreibung> "
                               "[antwort-text]"}
        else:
            resp = args[2] if len(args) > 2 else None
            result = cmd_create_tool(args[0], args[1], resp)

    elif cmd == "activate":
        if not args:
            result = {"error": "Verwendung: activate <workflow-id>"}
        else:
            result = cmd_activate(args[0])

    elif cmd == "deactivate":
        if not args:
            result = {"error": "Verwendung: deactivate <workflow-id>"}
        else:
            result = cmd_deactivate(args[0])

    # ─── Registry-Befehle ───────────────────────────────────

    elif cmd == "list":
        result = cmd_list()

    elif cmd == "call":
        if not args:
            result = {"error": "Verwendung: call <tool-name> [json-params]"}
        else:
            params = parse_json_arg(args[1]) if len(args) > 1 else {}
            result = cmd_call(args[0], params)

    elif cmd == "register":
        if len(args) < 3:
            result = {"error": "Verwendung: register <name> <webhook-pfad> "
                               "<beschreibung> [params-json]"}
        else:
            params = parse_json_arg(args[3]) if len(args) > 3 else {}
            wf_id = args[4] if len(args) > 4 else ""
            result = cmd_register(args[0], args[1], args[2], params, wf_id)

    elif cmd == "unregister":
        if not args:
            result = {"error": "Verwendung: unregister <name>"}
        else:
            result = cmd_unregister(args[0])

    elif cmd == "discover":
        result = cmd_discover()

    # ─── Diagnose-Befehle ───────────────────────────────────

    elif cmd == "test":
        result = cmd_test()

    elif cmd == "status":
        result = cmd_status()

    # ─── Unbekannter Befehl ─────────────────────────────────

    else:
        result = {
            "error": f"Unbekannter Befehl: {cmd}",
            "verfuegbar": list(COMMANDS.keys()),
        }

    # Ausgabe + Exit-Code Contract
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(1 if _has_error(result) else 0)


if __name__ == "__main__":
    main()

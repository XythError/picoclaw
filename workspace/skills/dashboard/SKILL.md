---
name: dashboard
description: "Web dashboard management: create and update widgets, sync data from skills, manage interactive buttons and notifications. Use when the user wants to view or update the dashboard, add/remove widgets, check dashboard status, or integrate skill data into the dashboard."
---

# Dashboard Skill

Web dashboard with widgets, buttons, and notifications. Served locally on port 7000.

## Script

```bash
python3 skills/dashboard/scripts/dashboard.py <command>
```

## Guardrails

1. **No Dummy Data:** Never output placeholder or example values as real data.
2. **No Blind Writes:** Never edit `dashboard/data.json` directly. Use only `update-widget`, `sync-data`, template commands, and skill scripts.
3. **Freshness First:** Before user-visible responses for data-driven widgets, refresh the data source first (`sync-data` or a skill-specific fetch).
4. **Read-before-Write:** Read the existing widget before writing; only change the required fields.
5. **Interactive = Persistent:** Clicks/actions must be persisted server-side and remain consistent after reload.
6. **Fail Closed:** If a real data source fails, show an honest status in the widget instead of fake data.

## Server Commands

```bash
python3 skills/dashboard/scripts/dashboard.py ensure-running
python3 skills/dashboard/scripts/dashboard.py status
python3 skills/dashboard/scripts/dashboard.py restart
python3 skills/dashboard/scripts/dashboard.py health
```

## Widget Commands

```bash
python3 skills/dashboard/scripts/dashboard.py update-widget <id> '<json>'
python3 skills/dashboard/scripts/dashboard.py remove-widget <id>
python3 skills/dashboard/scripts/dashboard.py sync-data
```

## Template Commands

```bash
python3 skills/dashboard/scripts/dashboard.py export-widget-templates
python3 skills/dashboard/scripts/dashboard.py list-widget-templates
python3 skills/dashboard/scripts/dashboard.py save-widget-template <widget-id> [template-name]
python3 skills/dashboard/scripts/dashboard.py apply-widget-template <template-name> [new-widget-id]
```

## Watchdog

```bash
python3 skills/dashboard/scripts/watchdog.py ensure-running
python3 skills/dashboard/scripts/watchdog.py status
python3 skills/dashboard/scripts/watchdog.py install-cron
```

## Widget Schema

```json
{
  "id": "widget-id",
  "type": "widget-type",
  "title": "Title",
  "size": "small|medium|large",
  "data": {}
}
```

## New Widget Workflow

1. **Clarify intent:** What should the user see or control live?
2. **Identify data source:** Determine the real data source (existing skill or new skill).
3. **Choose widget:** Extend an existing widget or apply a template.
4. **Minimal change:** Use `update-widget` to set only the required fields.
5. **Populate data:** Sync real data (`sync-data` or a skill-specific fetch).
6. **Test interaction:** Click/action → persistence → reload check.
7. **Save template:** When structure is stable, use `save-widget-template`.

## Skill Integration Contract

When integrating a skill into the dashboard:

1. Skill delivers current data in machine-readable format (JSON).
2. Dashboard receives a clear mapper: Skill-JSON → Widget `data`.
3. Interactions use unique actions (`<skill>-<action>`) with server-side persistence.
4. Error path returns a status text, never fake data.
5. After integration: verify `status`, `sync-data`, and interaction behavior.

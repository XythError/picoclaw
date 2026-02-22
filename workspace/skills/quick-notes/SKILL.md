---
name: quick-notes
description: Notizen hinzufügen, auflisten und durchsuchen. Nutze bei: Notiz hinzufügen, Notizen auflisten, Notiz suchen.
---

# Quick Notes

Dieser Skill ermöglicht das Verwalten von Notizen in einer einfachen Textdatei.

## Workflow / Befehle / API

### Notiz hinzufügen
```bash
python3 skills/quick-notes/scripts/add.py "Deine Notiz hier"
```

### Notizen auflisten
```bash
python3 skills/quick-notes/scripts/list.py
```

### Notiz suchen
```bash
python3 skills/quick-notes/scripts/search.py "Suchbegriff"
```

## Regeln / Hinweise
- Alle Notizen werden in der Datei `~/.picoclaw/workspace/notes.txt` gespeichert.
- Jede Notiz wird in einer neuen Zeile hinzugefügt.
- Alle Befehle liefern JSON auf stdout (`ok`, `error`, `count`, etc.).
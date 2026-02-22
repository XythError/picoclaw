#!/usr/bin/env python3
"""Notiz hinzufügen."""
import sys
import json
from pathlib import Path


NOTES_FILE = Path.home() / ".picoclaw" / "workspace" / "notes.txt"

if len(sys.argv) < 2:
    print(json.dumps({"ok": False, "error": {"code": "usage", "message": "Usage: add.py <notiz>"}}, ensure_ascii=False))
    sys.exit(1)

notiz = ' '.join(sys.argv[1:])
NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(NOTES_FILE, 'a', encoding='utf-8') as f:
    f.write(notiz + '\n')
print(json.dumps({"ok": True, "message": "Notiz hinzugefügt", "note": notiz, "file": str(NOTES_FILE)}, ensure_ascii=False))
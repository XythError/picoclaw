#!/usr/bin/env python3
"""Notiz suchen."""
import sys
import json
from pathlib import Path


NOTES_FILE = Path.home() / ".picoclaw" / "workspace" / "notes.txt"

if len(sys.argv) < 2:
    print(json.dumps({"ok": False, "error": {"code": "usage", "message": "Usage: search.py <suchbegriff>"}}, ensure_ascii=False))
    sys.exit(1)

suchbegriff = sys.argv[1]
try:
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        notes = [line.strip() for line in f.readlines() if line.strip()]
    matches = [note for note in notes if suchbegriff.lower() in note.lower()]
    print(json.dumps({"ok": True, "query": suchbegriff, "count": len(matches), "matches": matches, "file": str(NOTES_FILE)}, ensure_ascii=False))
except FileNotFoundError:
    print(json.dumps({"ok": True, "query": suchbegriff, "count": 0, "matches": [], "file": str(NOTES_FILE)}, ensure_ascii=False))
#!/usr/bin/env python3
"""Notizen auflisten."""
import json
from pathlib import Path


NOTES_FILE = Path.home() / ".picoclaw" / "workspace" / "notes.txt"

try:
    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        notes = [line.strip() for line in f.readlines() if line.strip()]
    print(json.dumps({"ok": True, "count": len(notes), "notes": notes, "file": str(NOTES_FILE)}, ensure_ascii=False))
except FileNotFoundError:
    print(json.dumps({"ok": True, "count": 0, "notes": [], "file": str(NOTES_FILE)}, ensure_ascii=False))
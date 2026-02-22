#!/usr/bin/env python3
"""
Morgen-Routine: Haushalt + Kalender.
Taeglich 07:00 via Cron (deliver:true → Telegram).
1. Zeigt heutige Aufgaben + Termine (via haushalt.py heute)
2. Dreht Rotation weiter
3. Fragt was heute noch ansteht
"""

import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from haushalt import (
    load_state, get_todays_tasks, get_calendar_events,
    get_todos, advance, get_today_info, TAGE_KURZ
)


def build_morning_message():
    state = load_state()
    info = get_today_info()

    lines = []
    lines.append(f"☀️ Guten Morgen! {info['weekday_name']}, {info['date']} (KW {info['kw']})")
    lines.append("")

    # Kalender-Termine (max 5 fuer Morgen-Nachricht)
    events = get_calendar_events(max_events=5, max_days=3)
    if events:
        lines.append("📅 Termine:")
        for ev in events:
            d = ev["start"].strftime("%d.%m.")
            day = TAGE_KURZ[ev["start"].weekday()]
            if ev["allday"]:
                lines.append(f"   • {day} {d} {ev['summary']}")
            else:
                t = ev["start"].strftime("%H:%M")
                lines.append(f"   • {day} {d} {t} {ev['summary']}")
        lines.append("")

    # Haushaltsaufgaben
    tasks = get_todays_tasks(state)
    if tasks:
        lines.append("🧹 Haushalt heute:")
        for t in tasks:
            lines.append(f"   • {t['display']}")
        lines.append("")

    # TODOs
    todos = get_todos(state)
    if todos:
        lines.append(f"\U0001f4cb TODOs ({len(todos)}):")
        for t in todos:
            dl = f" (bis {t['deadline']})" if "deadline" in t else ""
            lines.append(f"   \u2022 {t['text']}{dl}")
        lines.append("")

    lines.append("\u2753 Was steht heute noch an?")
    return "\n".join(lines)


def main():
    # Nachricht BEVOR Rotation (damit heutige Aufgaben angezeigt werden)
    msg = build_morning_message()

    # Rotation weiterdrehen
    state = load_state()
    advance(state)

    print(msg)


if __name__ == "__main__":
    main()

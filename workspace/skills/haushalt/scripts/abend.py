#!/usr/bin/env python3
"""
Abend-Check: Offene TODOs abfragen.
Taeglich 18:00 via Cron (deliver:true → Telegram).
Listet offene TODOs und fragt welche erledigt sind.
"""

import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from haushalt import load_state, get_todos, get_today_info


def build_evening_message():
    state = load_state()
    info = get_today_info()
    todos = get_todos(state)

    lines = []
    lines.append(f"🌆 Abend-Check — {info['weekday_name']}, {info['date']}")
    lines.append("")

    if not todos:
        lines.append("✅ Keine offenen TODOs — alles erledigt! 🎉")
        return "\n".join(lines)

    lines.append(f"📋 Offene TODOs ({len(todos)}):")
    for i, t in enumerate(todos, 1):
        dl = ""
        if "deadline" in t:
            deadline = datetime.strptime(t["deadline"], "%Y-%m-%d")
            days_left = (deadline - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).days
            if days_left < 0:
                dl = f" ⚠️ ÜBERFÄLLIG seit {abs(days_left)}d!"
            elif days_left == 0:
                dl = " ⚠️ Heute fällig!"
            elif days_left <= 2:
                dl = f" ⏰ Noch {days_left}d"
            else:
                dl = f" (bis {t['deadline']})"
        lines.append(f"   {i}. {t['text']}{dl}")

    lines.append("")
    lines.append("Hast du heute etwas davon erledigt? Sag mir einfach was fertig ist!")

    return "\n".join(lines)


def main():
    msg = build_evening_message()
    print(msg)


if __name__ == "__main__":
    main()

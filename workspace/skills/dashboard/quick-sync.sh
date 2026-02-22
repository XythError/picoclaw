#!/bin/bash
# Dashboard Auto-Sync Quick Reference

WORKSPACE="$HOME/.picoclaw/workspace"
cd "$WORKSPACE"

echo "🦞 Dashboard Auto-Sync Quick Reference"
echo ""

echo "📊 Dashboard URL:"
echo "   http://192.168.2.50:7000/"
echo ""

echo "🔄 Manuelle Synchronisierung:"
echo "   python3 skills/dashboard/scripts/dashboard.py sync-data"
echo ""

echo "📋 Dashboard-Status:"
echo "   python3 skills/dashboard/scripts/dashboard.py status"
echo ""

echo "🆕 Neue Widgets:"
echo "   - calendar (Termine)"
echo "   - todos (Offene TODOs)"
echo ""

echo "⚙️ Cron-Job:"
echo "   Läuft alle 15 Minuten automatisch"
echo "   Befehl: python3 skills/dashboard/scripts/dashboard.py sync-data"
echo ""

echo "🎯 Was synchronisiert wird:"
echo "   1. Kalender-Termine (cloud/Calendar/personal/)"
echo "   2. Haushalt-Aufgaben (haushalt.py json)"
echo "   3. Offene TODOs (haushalt.py todo-list)"
echo ""

echo "✨ Interaktionen:"
echo "   - Klick auf Task → abhaken (mit Animation)"
echo "   - Klick auf TODO → abhaken & entfernen"
echo "   - Benachrichtigungen bestätigen Aktionen"
echo ""

echo "📝 Dokumentation:"
echo "   ~/.picoclaw/workspace/skills/dashboard/DASHBOARD-SYNC.md"
echo ""

echo "✅ Status: Production Ready"

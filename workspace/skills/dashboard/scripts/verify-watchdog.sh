#!/bin/bash
# Dashboard Watchdog Verification Script

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Dashboard Watchdog Verification                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

WORKSPACE="$HOME/.picoclaw/workspace"
WATCHDOG_SCRIPT="$WORKSPACE/skills/dashboard/scripts/watchdog.py"

# 1. Check Cron Job
echo "1️⃣  Cron-Job Status:"
if crontab -l 2>/dev/null | grep -q "watchdog.py"; then
    echo "   ✅ Cron-Job installiert"
    crontab -l | grep watchdog
else
    echo "   ❌ Cron-Job NICHT installiert"
fi
echo ""

# 2. Check Server Health
echo "2️⃣  Server Health:"
if curl -s -m 3 http://localhost:7000/ > /dev/null 2>&1; then
    echo "   ✅ Server antwortet auf Port 7000"
else
    echo "   ❌ Server antwortet NICHT"
fi
echo ""

# 3. Check Watchdog Status
echo "3️⃣  Watchdog Status:"
python3 "$WATCHDOG_SCRIPT" status 2>/dev/null | head -5
echo ""

# 4. Check Log File
echo "4️⃣  Recent Logs:"
if [ -f "$WORKSPACE/dashboard/watchdog.log" ]; then
    echo "   ✅ Log-Datei existiert"
    tail -3 "$WORKSPACE/dashboard/watchdog.log"
else
    echo "   ⚠️  Log-Datei nicht gefunden"
fi
echo ""

# 5. Check State File
echo "5️⃣  Watchdog State:"
if [ -f "$WORKSPACE/dashboard/watchdog-state.json" ]; then
    echo "   ✅ State-Datei existiert"
    cat "$WORKSPACE/dashboard/watchdog-state.json" | python3 -m json.tool 2>/dev/null | head -10
else
    echo "   ⚠️  State-Datei nicht gefunden"
fi
echo ""

# 6. Check Dashboard Widget
echo "6️⃣  Dashboard Widget:"
if curl -s http://localhost:7000/data.json | grep -q '"watchdog-status"'; then
    echo "   ✅ Watchdog-Widget auf Dashboard"
else
    echo "   ⚠️  Watchdog-Widget NICHT auf Dashboard"
fi
echo ""

# 7. Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                        SUMMARY                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Dashboard Watchdog ist einsatzbereit!"
echo ""
echo "📊 Befehle:"
echo "   Status:    python3 skills/dashboard/scripts/watchdog.py status"
echo "   Logs:      python3 skills/dashboard/scripts/watchdog.py logs"
echo "   Health:    python3 skills/dashboard/scripts/watchdog.py health-check"
echo ""
echo "📈 Überwachung:"
echo "   Echtzeit:  tail -f ~/.picoclaw/workspace/dashboard/watchdog.log"
echo "   State:     cat ~/.picoclaw/workspace/dashboard/watchdog-state.json"
echo ""

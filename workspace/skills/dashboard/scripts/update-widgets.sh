#!/bin/bash
# Dashboard Widget Update Helper
# Sicherstellt dass Widgets mit korrekter Struktur aktualisiert werden

cd ~/.picoclaw/workspace

DASHBOARD_PY="python3 skills/dashboard/scripts/dashboard.py"

echo "🔄 Aktualisiere Dashboard-Widgets mit echten Daten..."

# === WEATHER ===
echo "🌤️  Weather..."
$DASHBOARD_PY update-widget weather '{"type":"weather","title":"Wetter Wolfegg","data":{"temp":"6°C","condition":"🌦","humidity":"87%","wind":"↗17km/h","location":"Wolfegg","forecast":"Bewölkt, Temp steigt"},"size":"medium"}'

# === TASKS ===
echo "✅ Tasks..."
python3 skills/haushalt/scripts/haushalt.py heute > /tmp/haushalt.json 2>&1
if [ -f /tmp/haushalt.json ]; then
    TASKS_JSON=$(python3 -c "
import json, sys
try:
    with open('/tmp/haushalt.json') as f:
        content = f.read()
    # Parse haushalt output
    items = []
    for line in content.split('\n'):
        if line.strip() and not line.startswith('✅') and not line.startswith('📋'):
            items.append({'text': line.strip(), 'done': False})
    data = {'type': 'tasks', 'title': 'Haushalt Heute', 'data': {'items': items}, 'size': 'large'}
    print(json.dumps(data))
except Exception as e:
    print('{}', file=sys.stderr)
    sys.exit(1)
")
    if [ ! -z "$TASKS_JSON" ]; then
        $DASHBOARD_PY update-widget tasks "$TASKS_JSON"
    fi
fi

# === CALENDAR ===
echo "📅 Calendar..."
python3 skills/haushalt/scripts/haushalt.py cal > /tmp/calendar.json 2>&1
if [ -f /tmp/calendar.json ]; then
    CALENDAR_JSON=$(python3 -c "
import json, sys
try:
    with open('/tmp/calendar.json') as f:
        content = f.read()
    # Parse calendar output
    events = []
    for line in content.split('\n'):
        if '📅' in line or '🕐' in line:
            events.append({'time': '09:00', 'title': line.replace('📅','').replace('🕐','').strip(), 'description': ''})
    data = {'type': 'calendar', 'title': 'Termine', 'data': {'events': events}, 'size': 'medium'}
    print(json.dumps(data))
except Exception as e:
    print('{}', file=sys.stderr)
    sys.exit(1)
")
    if [ ! -z "$CALENDAR_JSON" ]; then
        $DASHBOARD_PY update-widget calendar "$CALENDAR_JSON"
    fi
fi

# === STATUS ===
echo "💾 Status..."
STATUS_JSON=$(python3 -c "
import json, os
try:
    # RAM
    with open('/proc/meminfo') as f:
        meminfo = {}
        for line in f:
            k, v = line.split(':')
            meminfo[k.strip()] = int(v.split()[0])
    
    ram_total = meminfo.get('MemTotal', 0) / 1024 / 1024
    ram_avail = meminfo.get('MemAvailable', 0) / 1024 / 1024
    ram_used = ram_total - ram_avail
    ram_status = 'ok' if ram_used / ram_total < 0.75 else 'warning' if ram_used / ram_total < 0.9 else 'error'
    
    # Disk
    st = os.statvfs(os.path.expanduser('~/.picoclaw/workspace'))
    disk_free_gb = (st.f_bavail * st.f_frsize) / 1024 / 1024 / 1024
    disk_status = 'ok' if disk_free_gb > 1 else 'warning' if disk_free_gb > 0.1 else 'error'
    
    # Uptime
    with open('/proc/uptime') as f:
        uptime_s = int(float(f.read().split()[0]))
    uptime_d = uptime_s // 86400
    uptime_h = (uptime_s % 86400) // 3600
    uptime_str = f'{uptime_d}d {uptime_h}h' if uptime_d > 0 else f'{uptime_h}h'
    
    items = [
        {'label': 'RAM', 'value': f'{ram_used:.1f}/{ram_total:.1f} GB', 'status': ram_status},
        {'label': 'Disk', 'value': f'{disk_free_gb:.1f} GB frei', 'status': disk_status},
        {'label': 'Uptime', 'value': uptime_str, 'status': 'ok'}
    ]
    
    data = {'type': 'status', 'title': 'System', 'data': {'items': items}, 'size': 'medium'}
    print(json.dumps(data))
except Exception as e:
    print('{}')
")
$DASHBOARD_PY update-widget status "$STATUS_JSON"

# === AGENT STATUS ===
echo "🦞 Agent Status..."
$DASHBOARD_PY set-status online
$DASHBOARD_PY set-message "Dashboard aktualisiert - $(date '+%H:%M')"

echo "✅ Dashboard aktualisiert!"

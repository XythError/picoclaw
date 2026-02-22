---
name: dashboard
description: "Create terminal-based dashboards to display metrics, logs, and system information in a structured, real-time view. Use when the user wants to monitor system stats, application metrics, log streams, or build a custom TUI dashboard using tools like btop, glow, tmux layouts, or shell scripts."
metadata: {"nanobot":{"emoji":"📊","os":["darwin","linux"]}}
---

# Dashboard Skill

Build and use terminal dashboards for monitoring and displaying information.

## Quick Dashboard Tools

### btop (system resources)
```bash
btop                  # Interactive CPU/memory/disk/network monitor
btop --utf-force      # Force UTF-8 box drawing characters
```

### watch (auto-refresh any command)
```bash
watch -n 2 'df -h'                    # Disk usage, refresh every 2s
watch -n 1 'ps aux --sort=-%cpu | head -15'  # Top CPU processes
watch -d -n 5 'netstat -an | grep ESTABLISHED | wc -l'  # Connection count
```

### tmux multi-pane dashboard

Create a monitoring layout with multiple panes:

```bash
SESSION="dashboard"
SOCKET="${TMPDIR:-/tmp}/dashboard.sock"

tmux -S "$SOCKET" new-session -d -s "$SESSION" -x 220 -y 50

# Split into panes
tmux -S "$SOCKET" split-window -h -t "$SESSION"
tmux -S "$SOCKET" split-window -v -t "$SESSION":0.0
tmux -S "$SOCKET" split-window -v -t "$SESSION":0.1

# Assign content to each pane
tmux -S "$SOCKET" send-keys -t "$SESSION":0.0 'watch -n 2 "df -h"' Enter
tmux -S "$SOCKET" send-keys -t "$SESSION":0.1 'htop' Enter
tmux -S "$SOCKET" send-keys -t "$SESSION":0.2 'watch -n 5 "free -h"' Enter
tmux -S "$SOCKET" send-keys -t "$SESSION":0.3 'tail -f /var/log/syslog' Enter

# Attach
tmux -S "$SOCKET" attach -t "$SESSION"
```

## System Metrics Dashboard (Shell Script)

Quick ASCII dashboard printed to terminal:

```bash
#!/usr/bin/env bash
while true; do
  clear
  echo "═══════════════════════════════════════"
  echo "  SYSTEM DASHBOARD — $(date '+%Y-%m-%d %H:%M:%S')"
  echo "═══════════════════════════════════════"

  echo ""
  echo "── CPU ──────────────────────────────"
  top -bn1 | grep "Cpu(s)" | awk '{printf "  Usage: %.1f%%\n", 100-$8}'

  echo ""
  echo "── Memory ───────────────────────────"
  free -h | awk '/^Mem:/{printf "  Used: %s / %s\n", $3, $2}'

  echo ""
  echo "── Disk ─────────────────────────────"
  df -h / | awk 'NR==2{printf "  Root: %s used, %s free (%s)\n", $3, $4, $5}'

  echo ""
  echo "── Network ──────────────────────────"
  ip -s link show eth0 2>/dev/null | awk '/RX:/{getline; printf "  RX: %s bytes\n", $1}' || true
  ip -s link show eth0 2>/dev/null | awk '/TX:/{getline; printf "  TX: %s bytes\n", $1}' || true

  echo ""
  echo "── Top Processes ────────────────────"
  ps aux --sort=-%cpu | awk 'NR>1 && NR<=6{printf "  %-20s CPU: %s%%\n", $11, $3}'

  sleep 5
done
```

## Log Streaming Dashboard

```bash
# Multi-source log watcher with color
tail -f /var/log/syslog /var/log/auth.log 2>/dev/null | \
  grep --line-buffered -E "(error|warn|crit)" --color=always
```

## Custom Metrics

For application-specific dashboards, see `references/dashboard-patterns.md` for:
- Prometheus/Grafana integration
- JSON metrics display with `jq`
- HTTP endpoint polling patterns
- Time-series data in the terminal

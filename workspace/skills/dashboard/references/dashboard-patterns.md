# Dashboard Patterns Reference

## Prometheus Metrics Polling

```bash
# Query Prometheus HTTP API
PROM="http://localhost:9090"

# Current value of a metric
curl -s "$PROM/api/v1/query?query=up" | jq '.data.result[] | {job: .metric.job, value: .value[1]}'

# Range query (last 1 hour, 1-minute steps)
curl -s "$PROM/api/v1/query_range?query=rate(http_requests_total[5m])&start=$(date -d '1 hour ago' +%s)&end=$(date +%s)&step=60" | \
  jq '.data.result[0].values[-1]'

# Watch metric live
watch -n 5 'curl -s "http://localhost:9090/api/v1/query?query=node_memory_MemAvailable_bytes" | jq ".data.result[0].value[1]" | numfmt --from=none --to=iec'
```

## JSON Metrics Display with jq

```bash
# Format JSON metric as table
curl -s http://localhost:8080/metrics | jq -r '
  .services[] |
  [.name, .status, (.latency_ms | tostring) + "ms"] |
  @tsv
' | column -t

# Color-coded status (uses tput for portability)
GREEN=$(tput setaf 2 2>/dev/null || printf '')
RED=$(tput setaf 1 2>/dev/null || printf '')
RESET=$(tput sgr0 2>/dev/null || printf '')

curl -s http://localhost:8080/health | jq -r '.checks[] | [.status, .name, (.message // "")] | @tsv' | \
  while IFS=$'\t' read -r status name message; do
    if [[ "$status" == "ok" ]]; then
      printf "%s✓%s %s\n" "$GREEN" "$RESET" "$name"
    else
      printf "%s✗%s %s: %s\n" "$RED" "$RESET" "$name" "$message"
    fi
  done
```

## HTTP Endpoint Polling

```bash
# Poll endpoint and alert on non-200
while true; do
  STATUS=$(curl -o /dev/null -s -w "%{http_code}" https://example.com/health)
  TIMESTAMP=$(date '+%H:%M:%S')
  if [[ "$STATUS" != "200" ]]; then
    echo "[$TIMESTAMP] ⚠️  Status: $STATUS"
  else
    echo "[$TIMESTAMP] ✅ OK ($STATUS)"
  fi
  sleep 30
done
```

## Terminal Sparklines

Simple ASCII sparkline using bash arrays:

```bash
# Capture a series of values and render as sparkline
sparkline() {
  local vals=("$@")
  local chars=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█")
  local min=${vals[0]} max=${vals[0]}
  for v in "${vals[@]}"; do
    (( v < min )) && min=$v
    (( v > max )) && max=$v
  done
  local range=$(( max - min ))
  [[ $range -eq 0 ]] && range=1
  local result=""
  for v in "${vals[@]}"; do
    local idx=$(( (v - min) * 7 / range ))
    result+="${chars[$idx]}"
  done
  echo "$result"
}

# Example: CPU usage last 10 samples
samples=(23 45 67 32 56 78 43 61 29 52)
sparkline "${samples[@]}"
# Output: ▁▄▇▂▅█▃▆▁▅
```

## Resource Alert Thresholds

```bash
# Alert when disk usage exceeds 80%
check_disk() {
  local threshold=80
  df -h | awk -v t="$threshold" 'NR>1{
    gsub(/%/, "", $5)
    if ($5+0 >= t) printf "⚠️  %s is %s%% full\n", $6, $5
  }'
}

# Alert when memory usage exceeds 90%
check_memory() {
  local threshold=90
  free | awk -v t="$threshold" '/Mem:/{
    pct = int($3/$2*100)
    if (pct >= t) printf "⚠️  Memory: %d%% used\n", pct
  }'
}
```

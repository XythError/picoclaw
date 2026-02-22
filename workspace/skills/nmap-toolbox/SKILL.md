---
name: nmap-toolbox
description: "Network scanning and reconnaissance with nmap. Use when performing port scans, service/version detection, OS fingerprinting, network discovery, firewall analysis, or running NSE scripts for vulnerability checks."
metadata: {"nanobot":{"emoji":"🔍","os":["darwin","linux"],"requires":{"bins":["nmap"]},"install":[{"id":"brew","kind":"brew","formula":"nmap","bins":["nmap"],"label":"Install nmap (brew)"},{"id":"apt","kind":"apt","package":"nmap","bins":["nmap"],"label":"Install nmap (apt)"}]}}
---

# Nmap Toolbox

Use `nmap` for network discovery and security auditing.

> **Legal note:** Only scan networks and hosts you own or have explicit written permission to test.

## Common Scans

```bash
# Host discovery (no port scan)
nmap -sn 192.168.1.0/24

# Fast port scan (top 1000 ports, no DNS resolution)
nmap -F -n 192.168.1.1

# Full TCP connect scan (no root required)
nmap -sT 192.168.1.1

# SYN scan (fast, requires root/sudo)
sudo nmap -sS 192.168.1.1

# All ports
sudo nmap -p- 192.168.1.1

# Specific ports
nmap -p 22,80,443,8080 192.168.1.1

# Port range
nmap -p 1-1024 192.168.1.1
```

## Service & Version Detection

```bash
# Version detection
nmap -sV 192.168.1.1

# Aggressive scan (version, OS, scripts, traceroute)
sudo nmap -A 192.168.1.1

# OS detection only
sudo nmap -O 192.168.1.1
```

## Output Formats

```bash
# Save to all formats (normal, XML, grepable)
nmap -oA /tmp/scan_results 192.168.1.0/24

# XML output (parseable)
nmap -oX /tmp/scan.xml 192.168.1.1

# Grepable output
nmap -oG /tmp/scan.gnmap 192.168.1.1

# Parse grepable for open ports
grep "Ports:" /tmp/scan.gnmap | grep -oP '\d+/open'
```

## NSE Scripts (Nmap Scripting Engine)

```bash
# List available scripts
ls /usr/share/nmap/scripts/ | grep http

# Default scripts
sudo nmap -sC 192.168.1.1

# Specific script
sudo nmap --script http-title 192.168.1.1

# Script categories
sudo nmap --script "safe and discovery" 192.168.1.0/24

# Vulnerability check (use with caution)
sudo nmap --script vuln 192.168.1.1
```

## Performance & Timing

```bash
# Timing templates: T0 (paranoid) – T5 (insane)
nmap -T4 192.168.1.0/24         # T4 = aggressive (good for LANs)
nmap -T2 target.com             # T2 = polite (slower, less intrusive)

# Parallel host groups and probes
nmap --min-parallelism 100 --max-rtt-timeout 100ms 192.168.1.0/24
```

## Evasion & Stealth

```bash
# Fragment packets
sudo nmap -f 192.168.1.1

# Decoy scan (mix real IP with decoys)
sudo nmap -D RND:5 192.168.1.1

# Randomize host order
nmap --randomize-hosts 192.168.1.0/24

# Slow scan to avoid IDS
nmap -T1 --scan-delay 1s 192.168.1.1
```

## Useful Combinations

```bash
# Quick internal network audit
sudo nmap -sS -sV -T4 --open -oA /tmp/lan_audit 192.168.1.0/24

# Web server enumeration
sudo nmap -sV --script "http-*" -p 80,443,8080,8443 target.com

# SSH audit
sudo nmap --script ssh-auth-methods -p 22 192.168.1.1
```

## Reading Scan Results

See `references/nmap-output.md` for:
- Interpreting port states (open/closed/filtered)
- Understanding service version output
- Common NSE script output formats

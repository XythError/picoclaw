#!/usr/bin/env python3
"""
nmap-toolbox: Zuverlässiger nmap-Wrapper für Netzwerk-Scans.
Führt alle Scans mit Root-Rechten (su) aus für maximale Informationsbeschaffung.
"""
import subprocess
import json
import re
import sys
import argparse
from typing import Optional

NMAP_PATH = "/data/data/com.termux/files/usr/bin/nmap"

def _run_nmap_su(cmd: list, timeout: int = 120) -> dict:
    """Führt nmap als root (su) aus für maximale Rechte."""
    # cmd ist Liste von Flags, absoluter Pfad erforderlich
    cmd_str = " ".join(cmd)
    su_cmd = f"su -c '{NMAP_PATH} {cmd_str}'"
    
    try:
        result = subprocess.run(
            ["sh", "-c", su_cmd],
            capture_output=True,
            text=True,
            timeout=timeout + 30
        )
        output = result.stdout + result.stderr
        
        return {
            "success": result.returncode in [0, 1],
            "returncode": result.returncode,
            "raw_output": output,
            "parsed": _parse_nmap_output(output)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except FileNotFoundError:
        return {"success": False, "error": "su or nmap not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- Scan-Funktionen ---

def scan_ping(host: str, timeout: int = 30) -> dict:
    """Ping-Scan: Findet aktive Hosts im Netzwerk."""
    cmd = ["-sn", "-PR", "--max-retries", "2", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_ports(host: str, ports: str = "1-1000", timing: int = 3, timeout: int = 120) -> dict:
    """Port-Scan: Scannt offene Ports (SYN-Scan mit Root)."""
    cmd = ["-p", ports, "-sS", "-T", str(timing), "--max-retries", "2", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_top_ports(host: str, top: int = 100, timeout: int = 60) -> dict:
    """Top-Ports-Scan: Scannt die top-n häufigsten Ports."""
    cmd = ["--top-ports", str(top), "-sS", "-T3", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_service(host: str, ports: str = "1-1000", timeout: int = 180) -> dict:
    """Service-Scan: Erkennt Dienste und Versionen (mit -sV)."""
    cmd = ["-p", ports, "-sS", "-sV", "-T3", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_os(host: str, timeout: int = 180) -> dict:
    """OS-Detection: Errät das Betriebssystem (mit -O)."""
    cmd = ["-O", "-sS", "-T3", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_aggressive(host: str, timeout: int = 300) -> dict:
    """Aggressive Scan: -A = OS, Service, Script, Traceroute."""
    cmd = ["-A", "-sS", "-T3", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_network(subnet: str = "192.168.2.0/24", timeout: int = 120) -> dict:
    """Netzwerk-Scan: Findet alle aktiven Hosts im Subnetz."""
    cmd = ["-sn", "-PR", "--max-retries", "2", f"-host-timeout={timeout}s", subnet]
    return _run_nmap_su(cmd, timeout)

def scan_tcp_full(host: str, timeout: int = 300) -> dict:
    """Full-TCP-Scan: Alle 65535 TCP-Ports (SYN-Scan)."""
    cmd = ["-p-", "-sS", "-T3", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

def scan_udp_top(host: str, top: int = 100, timeout: int = 300) -> dict:
    """UDP-Top-Ports-Scan (erfordert Root)."""
    cmd = ["-sU", f"--top-ports", str(top), "-T2", f"-host-timeout={timeout}s", host]
    return _run_nmap_su(cmd, timeout)

# --- Hilfsfunktionen ---

def _parse_nmap_output(output: str) -> dict:
    """Parst nmap-Rohausgabe in strukturierte Daten."""
    parsed = {"hosts": [], "ports": [], "services": [], "os": None}
    
    # Hosts extrahieren
    host_blocks = re.split(r'Host:|Nmap scan report for', output)
    for block in host_blocks[1:]:
        host_info = {}
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', block)
        if ip_match:
            host_info["ip"] = ip_match.group(1)
        
        # Status
        if "Status: Up" in block or "Host is up" in block:
            host_info["status"] = "up"
        elif "Status: Down" in block or "Host is down" in block:
            host_info["status"] = "down"
        
        # MAC-Adresse
        mac_match = re.search(r'((?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2}))', block)
        if mac_match:
            host_info["mac"] = mac_match.group(1)
        
        # Hostname
        hostname_match = re.search(r'\(([^)]+)\)\s*$', block.split('\n')[0] if '\n' in block else block)
        if hostname_match:
            host_info["hostname"] = hostname_match.group(1)
        
        if host_info:
            parsed["hosts"].append(host_info)
    
    # Ports extrahieren
    port_section = re.search(r'PORT\s+STATE\s+SERVICE(.*?)(?:\n\n|\nHost|\Z)', output, re.DOTALL)
    if port_section:
        for line in port_section.group(1).strip().split('\n'):
            match = re.match(r'(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)', line)
            if match:
                parsed["ports"].append({
                    "port": int(match.group(1)),
                    "protocol": match.group(2),
                    "state": match.group(3),
                    "service": match.group(4)
                })
    
    # Services/Versionen
    if "/version" in output or "service version" in output.lower():
        svc_match = re.findall(r'(\d+)/(tcp|udp)\s+(\w+)\s+(\S+)\s+(.+)', output)
        for m in svc_match:
            parsed["services"].append({
                "port": int(m[0]),
                "protocol": m[1],
                "state": m[2],
                "service": m[3],
                "version": m[4] if len(m) > 4 else ""
            })
    
    # OS-Guess
    os_section = re.search(r'OS details: (.+)', output)
    if os_section:
        parsed["os"] = os_section.group(1)
    else:
        os_match = re.search(r'OS: (.+)', output)
        if os_match:
            parsed["os"] = os_match.group(1)
    
    return parsed

# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="nmap-toolbox")
    parser.add_argument("scan", choices=["ping", "ports", "top", "service", "os", "aggressive", "network", "tcp-full", "udp-top"], help="Scan-Typ")
    parser.add_argument("target", help="Ziel-IP oder Netzwerk")
    parser.add_argument("--ports", default="1-1000", help="Ports für port-scan")
    parser.add_argument("--top", type=int, default=100, help="Anzahl Top-Ports")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in Sekunden")
    parser.add_argument("--json", action="store_true", help="JSON-Output")
    
    args = parser.parse_args()
    
    scans = {
        "ping": lambda: scan_ping(args.target, args.timeout),
        "ports": lambda: scan_ports(args.target, args.ports, timeout=args.timeout),
        "top": lambda: scan_top_ports(args.target, args.top, args.timeout),
        "service": lambda: scan_service(args.target, args.ports, args.timeout),
        "os": lambda: scan_os(args.target, args.timeout),
        "aggressive": lambda: scan_aggressive(args.target, args.timeout),
        "network": lambda: scan_network(args.target, args.timeout),
        "tcp-full": lambda: scan_tcp_full(args.target, args.timeout),
        "udp-top": lambda: scan_udp_top(args.target, args.top, args.timeout),
    }
    
    result = scans[args.scan]()
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if not result.get("success"):
            print(f"Fehler: {result.get('error', 'unbekannt')}", file=sys.stderr)
            sys.exit(1)
        
        parsed = result.get("parsed", {})
        
        if parsed.get("hosts"):
            print("=== Hosts ===")
            for h in parsed["hosts"]:
                print(f"  {h.get('ip', '?')} - {h.get('status', '?')} ({h.get('mac', 'kein MAC')})")
        
        if parsed.get("ports"):
            print("=== Ports ===")
            for p in parsed["ports"][:20]:
                print(f"  {p['port']}/{p['protocol']} {p['state']} {p['service']}")
            if len(parsed["ports"]) > 20:
                print(f"  ... und {len(parsed['ports']) - 20} weitere")
        
        if parsed.get("os"):
            print(f"=== OS ===")
            print(f"  {parsed['os']}")

if __name__ == "__main__":
    main()
#!/data/data/com.termux/files/usr/bin/python3
# -*- coding: utf-8 -*-
"""
adguard-ctl.py - AdGuardHome Management Tool fuer PicoClaw

Alle Befehle kehren IMMER innerhalb von max. 15 Sekunden zurueck.
Kein Haengen, kein Blockieren, kein stdout-Leak.

Verwendung:
  python3 adguard-ctl.py <befehl> [argumente]

Prozess:   start | stop | restart | status
Config:    config [abschnitt] | rewrites | blocks
Rewrites:  rewrite-add <domain> <ip> | rewrite-del <domain>
Blocking:  block <service> | unblock <service>
Whitelist: whitelist-add <domain> | whitelist-del <domain>
DNS:       upstream <dns1> [dns2 ...]
"""

import subprocess
import sys
import os
import time

# === Pfade ===
AGH_BIN  = "/data/data/com.termux/files/home/AdGuardHome/AdGuardHome"
AGH_CONF = "/data/data/com.termux/files/home/AdGuardHome/AdGuardHome.yaml"
AGH_DATA = "/data/data/com.termux/files/home/AdGuardHome/data"
TMPDIR   = os.environ.get("TMPDIR", "/data/data/com.termux/files/usr/tmp")
TIMEOUT  = 12  # Sekunden max pro Shell-Befehl


# === Hilfsfunktionen ===

def run(cmd, timeout=TIMEOUT):
    """Shell-Befehl ausfuehren. Kehrt IMMER zurueck (max timeout Sek.)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT nach {}s - Befehl abgebrochen".format(timeout), 124
    except Exception as e:
        return "", str(e), 1


def su_run(cmd, timeout=TIMEOUT):
    """Befehl als root ausfuehren (via su -c). IMMER mit Timeout."""
    # Einfache Anfuehrungszeichen im Befehl escapen
    escaped = cmd.replace("'", "'\\''")
    return run("su -c '{}'".format(escaped), timeout)


def su_start_daemon(cmd, timeout=TIMEOUT):
    """Daemon als root starten. Verwendet setsid fuer saubere Trennung.
    Kehrt IMMER zurueck dank subprocess.timeout."""
    try:
        proc = subprocess.run(
            ["su", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
            start_new_session=True
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT nach {}s".format(timeout), 124
    except Exception as e:
        return "", str(e), 1


def _extract_pids_from_lines(text):
    pids = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        for token in parts:
            if token.isdigit():
                pids.append(token)
                break
    return pids


def get_pids():
    """AdGuardHome-PIDs finden."""
    pids = []

    # 1) Root-Kontext: auf Android/Termux sind root-Prozesse oft nur via su sichtbar
    out, _, rc = su_run("ps -A -o pid,args 2>/dev/null | grep '[A]dGuardHome' | grep -v python")
    if rc == 0 and out:
        pids.extend(_extract_pids_from_lines(out))

    # 2) Fallback: user-Kontext
    if not pids:
        out, _, _ = run("ps -A -o pid,args 2>/dev/null | grep '[A]dGuardHome' | grep -v python")
        pids.extend(_extract_pids_from_lines(out))

    # 3) Fallback ueber offene Sockets (53/8080/3000)
    if not pids:
        out, _, rc = su_run("ss -tulnp 2>/dev/null | grep -E ':(53|8080|3000) '")
        if rc == 0 and out:
            for chunk in out.split('pid=')[1:]:
                pid_chars = []
                for ch in chunk:
                    if ch.isdigit():
                        pid_chars.append(ch)
                    else:
                        break
                pid = ''.join(pid_chars)
                if pid:
                    pids.append(pid)

    # unique + stable order
    seen = set()
    unique = []
    for pid in pids:
        if pid not in seen:
            unique.append(pid)
            seen.add(pid)
    return unique


def is_running():
    return len(get_pids()) > 0


# === Prozess-Verwaltung ===

def cmd_status():
    pids = get_pids()
    if pids:
        print("AdGuardHome: LAEUFT (PID: {})".format(", ".join(pids)))
        out, _, _ = su_run("ss -tulnp 2>/dev/null | grep ':53 '")
        if out:
            print("DNS Port 53: AKTIV")
        else:
            print("DNS Port 53: NICHT AKTIV (noch am Starten?)")
        out, _, _ = su_run("ss -tulnp 2>/dev/null | grep ':8080 '")
        if out:
            print("Web-UI Port 8080: AKTIV")
        else:
            print("Web-UI Port 8080: NICHT AKTIV")
    else:
        print("AdGuardHome: GESTOPPT")
    return 0


def cmd_start():
    pids = get_pids()
    if pids:
        print("AdGuardHome laeuft bereits (PID: {})".format(", ".join(pids)))
        return 0

    # DAEMON-START: su -c 'AGH' als detached Prozess (Popen, kein Wait).
    # KEIN nohup, KEIN & innerhalb su! su bleibt als Parent von AGH am Leben.
    # start_new_session=True trennt vom Python-Prozessbaum ab.
    try:
        subprocess.Popen(
            ["su", "-c", "{} -c {} -w {}".format(AGH_BIN, AGH_CONF, AGH_DATA)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except Exception as e:
        print("FEHLER: Start fehlgeschlagen: {}".format(e))
        return 1

    # Warten und verifizieren (5s fuer langsame Hardware)
    time.sleep(5)
    pids = get_pids()
    if pids:
        print("OK: AdGuardHome gestartet (PID: {})".format(", ".join(pids)))
        return 0
    else:
        print("FEHLER: AdGuardHome nicht gestartet")
        # Versuch, Fehlerausgabe direkt zu lesen
        _, direct_err, _ = su_run(
            "{} -c {} -w {} --check-config 2>&1 || echo CONF_ERR".format(
                AGH_BIN, AGH_CONF, AGH_DATA
            )
        )
        if direct_err:
            print("Config-Check: {}".format(direct_err))
        return 1


def cmd_stop():
    pids = get_pids()
    if not pids:
        print("AdGuardHome laeuft nicht")
        return 0

    su_run("kill {}".format(" ".join(pids)))
    time.sleep(2)

    pids = get_pids()
    if not pids:
        print("OK: AdGuardHome gestoppt")
        return 0

    # Force kill
    su_run("kill -9 {}".format(" ".join(pids)))
    time.sleep(1)

    pids = get_pids()
    if not pids:
        print("OK: AdGuardHome gestoppt (force)")
        return 0
    else:
        print("FEHLER: AdGuardHome konnte nicht gestoppt werden (PIDs: {})".format(
            ", ".join(pids)
        ))
        return 1


def cmd_restart():
    was_running = is_running()
    if was_running:
        rc = cmd_stop()
        if rc != 0:
            return rc
        time.sleep(1)
    return cmd_start()


# === Config lesen/schreiben ===

def read_config():
    """Config-Datei als Text lesen (via su)."""
    out, err, rc = su_run("cat " + AGH_CONF, timeout=5)
    if rc != 0:
        print("FEHLER: Config nicht lesbar: {}".format(err))
        return None
    return out


def write_config(content):
    """Config-Datei schreiben (via su + temp file)."""
    tmp = os.path.join(TMPDIR, "agh_config_tmp.yaml")
    try:
        with open(tmp, "w") as f:
            f.write(content)
        os.chmod(tmp, 0o644)
        _, err, rc = su_run("cp {} {}".format(tmp, AGH_CONF))
        if rc != 0:
            print("FEHLER beim Schreiben: {}".format(err))
            return False
        return True
    except Exception as e:
        print("FEHLER: {}".format(e))
        return False
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def cmd_config_show(section=None):
    config = read_config()
    if config is None:
        return 1
    if section:
        lines = config.split("\n")
        in_section = False
        result = []
        for line in lines:
            if line.rstrip() == section + ":":
                in_section = True
                result.append(line)
            elif in_section:
                if line and not line[0].isspace() and line[0] != "#":
                    break
                result.append(line)
        if result:
            print("\n".join(result))
        else:
            print("Abschnitt '{}' nicht gefunden".format(section))
            print("Verfuegbare Abschnitte: " + ", ".join(
                l.rstrip(":") for l in config.split("\n")
                if l and not l[0].isspace() and l.endswith(":")
            ))
    else:
        print(config)
    return 0


# === DNS-Rewrites ===

def parse_rewrites(config):
    """Alle DNS-Rewrites aus Config extrahieren."""
    lines = config.split("\n")
    rewrites = []
    in_rewrites = False
    current = {}
    for line in lines:
        stripped = line.strip()
        if "  rewrites:" in line and "rewrites_enabled" not in line:
            in_rewrites = True
            continue
        if in_rewrites:
            if stripped.startswith("- domain:"):
                if current:
                    rewrites.append(current)
                current = {"domain": stripped.split("domain:")[1].strip()}
            elif "answer:" in stripped and current:
                current["answer"] = stripped.split("answer:")[1].strip()
            elif "enabled:" in stripped and current:
                current["enabled"] = stripped.split("enabled:")[1].strip()
            elif stripped and not stripped.startswith("-") and not stripped.startswith("domain:") and not stripped.startswith("answer:") and not stripped.startswith("enabled:"):
                if not line.startswith("      ") and not line.startswith("    -"):
                    if current:
                        rewrites.append(current)
                    break
    if current and current not in rewrites:
        rewrites.append(current)
    return rewrites


def cmd_rewrite_list():
    config = read_config()
    if config is None:
        return 1
    rewrites = parse_rewrites(config)
    if rewrites:
        print("DNS-Rewrites ({} Eintraege):".format(len(rewrites)))
        for r in rewrites:
            status = "aktiv" if r.get("enabled", "true") == "true" else "inaktiv"
            print("  {} -> {} ({})".format(
                r.get("domain", "?"), r.get("answer", "?"), status
            ))
    else:
        print("Keine DNS-Rewrites konfiguriert")
    return 0


def cmd_rewrite_add(domain, ip):
    config = read_config()
    if config is None:
        return 1

    if "domain: {}".format(domain) in config:
        print("Rewrite fuer '{}' existiert bereits".format(domain))
        return 1

    new_entry = "    - domain: {}\n      answer: {}\n      enabled: true\n".format(
        domain, ip
    )
    # Vor safe_fs_patterns einfuegen (Ende der rewrites-Liste)
    if "  safe_fs_patterns:" in config:
        config = config.replace("  safe_fs_patterns:", new_entry + "  safe_fs_patterns:")
    else:
        print("FEHLER: Kann Einfuegeposition nicht finden")
        return 1

    if write_config(config):
        print("OK: DNS-Rewrite hinzugefuegt: {} -> {}".format(domain, ip))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


def cmd_rewrite_del(domain):
    config = read_config()
    if config is None:
        return 1

    if "domain: {}".format(domain) not in config:
        print("Kein Rewrite fuer '{}' gefunden".format(domain))
        return 0

    lines = config.split("\n")
    new_lines = []
    skip = 0
    for line in lines:
        if skip > 0:
            skip -= 1
            continue
        if "domain: {}".format(domain) in line:
            # Zeile mit - domain: und die folgenden 2 Zeilen (answer, enabled) ueberspringen
            if line.strip().startswith("- domain:"):
                skip = 2
                continue
        new_lines.append(line)

    if write_config("\n".join(new_lines)):
        print("OK: DNS-Rewrite entfernt: {}".format(domain))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


# === Blocked Services ===

def get_blocked_services(config):
    """Liste der blockierten Services extrahieren."""
    services = []
    lines = config.split("\n")
    in_ids = False
    for line in lines:
        stripped = line.strip()
        if stripped == "ids:" and "blocked_services" in "\n".join(lines[:lines.index(line)]):
            in_ids = True
            continue
        if in_ids:
            if stripped.startswith("- ") and line.startswith("      "):
                services.append(stripped[2:])
            elif stripped and not stripped.startswith("-"):
                break
    return services


def cmd_blocks_list():
    config = read_config()
    if config is None:
        return 1
    services = get_blocked_services(config)
    if services:
        print("Blockierte Dienste ({} Eintraege):".format(len(services)))
        for s in services:
            print("  - {}".format(s))
    else:
        print("Keine Dienste blockiert")
    return 0


def cmd_block(service):
    config = read_config()
    if config is None:
        return 1

    if "      - {}".format(service) in config:
        print("Service '{}' ist bereits blockiert".format(service))
        return 0

    lines = config.split("\n")
    new_lines = []
    in_ids = False
    added = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        stripped = line.strip()
        if stripped == "ids:" and not added:
            in_ids = True
            continue
        if in_ids and stripped.startswith("- ") and line.startswith("      "):
            # Pruefen ob naechste Zeile kein Service mehr ist
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if not next_stripped.startswith("- ") or not lines[i + 1].startswith("      "):
                    new_lines.append("      - {}".format(service))
                    in_ids = False
                    added = True

    if not added:
        # Fallback: Nach letztem ids-Eintrag einfuegen
        config_str = "\n".join(new_lines)
        # Finde die ids:-Zeile und fuege nach ihr ein
        config_str = config_str.replace("    ids:\n", "    ids:\n      - {}\n".format(service))
        new_lines = config_str.split("\n")
        added = True

    if write_config("\n".join(new_lines)):
        print("OK: Service '{}' blockiert".format(service))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


def cmd_unblock(service):
    config = read_config()
    if config is None:
        return 1

    target = "      - {}".format(service)
    if target not in config:
        print("Service '{}' ist nicht blockiert".format(service))
        return 0

    config = config.replace(target + "\n", "")
    if write_config(config):
        print("OK: Service '{}' entblockt".format(service))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


# === Whitelist ===

def cmd_whitelist_add(domain):
    config = read_config()
    if config is None:
        return 1

    rule = "@@||{}^$important".format(domain)
    if rule in config:
        print("Whitelist-Regel fuer '{}' existiert bereits".format(domain))
        return 0

    new_line = "  - '{}'\n".format(rule)
    config = config.replace("user_rules:\n", "user_rules:\n" + new_line)

    if write_config(config):
        print("OK: '{}' zur Whitelist hinzugefuegt".format(domain))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


def cmd_whitelist_del(domain):
    config = read_config()
    if config is None:
        return 1

    lines = config.split("\n")
    new_lines = [l for l in lines if not ("@@||{}^".format(domain) in l)]

    if len(new_lines) == len(lines):
        print("Keine Whitelist-Regel fuer '{}' gefunden".format(domain))
        return 0

    if write_config("\n".join(new_lines)):
        print("OK: '{}' von Whitelist entfernt".format(domain))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


# === Upstream DNS ===

def cmd_upstream_set(dns_list):
    config = read_config()
    if config is None:
        return 1

    lines = config.split("\n")
    new_lines = []
    in_upstream = False
    done = False
    for line in lines:
        stripped = line.strip()
        if "  upstream_dns:" in line and "file" not in line and not done:
            new_lines.append(line)
            for dns in dns_list:
                new_lines.append("    - {}".format(dns))
            in_upstream = True
            done = True
            continue
        if in_upstream:
            if line.startswith("    - "):
                continue  # Alte Eintraege ueberspringen
            else:
                in_upstream = False
        new_lines.append(line)

    if write_config("\n".join(new_lines)):
        print("OK: Upstream-DNS gesetzt:")
        for dns in dns_list:
            print("  - {}".format(dns))
        print("Neustart noetig: python3 adguard-ctl.py restart")
        return 0
    return 1


# === Hilfe ===

def usage():
    print("""adguard-ctl.py - AdGuardHome Management Tool

Verwendung: python3 adguard-ctl.py <befehl> [argumente]

Prozess-Verwaltung:
  start                       Starten (sicher, kehrt IMMER zurueck)
  stop                        Stoppen
  restart                     Neustarten
  status                      Status + Ports anzeigen

Konfiguration anzeigen:
  config                      Gesamte Config
  config <abschnitt>          Nur Abschnitt (dns, filtering, tls, ...)
  rewrites                    DNS-Rewrites auflisten
  blocks                      Blockierte Dienste auflisten

DNS-Rewrites:
  rewrite-add <domain> <ip>   Rewrite hinzufuegen
  rewrite-del <domain>        Rewrite entfernen

Dienste blockieren:
  block <service>             z.B. tiktok, facebook, instagram
  unblock <service>           Blockade aufheben

Whitelist:
  whitelist-add <domain>      Domain erlauben
  whitelist-del <domain>      Erlaubnis entfernen

Upstream-DNS:
  upstream <dns1> [dns2...]   DNS-Server setzen

Beispiele:
  python3 adguard-ctl.py start
  python3 adguard-ctl.py rewrite-add nas.home 192.168.2.100
  python3 adguard-ctl.py block facebook
  python3 adguard-ctl.py whitelist-add example.com
  python3 adguard-ctl.py upstream https://dns.quad9.net/dns-query""")


# === Main ===

def main():
    if len(sys.argv) < 2:
        usage()
        return 1

    cmd = sys.argv[1].lower()

    if cmd in ("start",):
        return cmd_start()
    elif cmd in ("stop",):
        return cmd_stop()
    elif cmd in ("restart", "neustart"):
        return cmd_restart()
    elif cmd in ("status",):
        return cmd_status()
    elif cmd in ("config",):
        section = sys.argv[2] if len(sys.argv) > 2 else None
        return cmd_config_show(section)
    elif cmd in ("rewrites", "rewrite-list"):
        return cmd_rewrite_list()
    elif cmd in ("rewrite-add",):
        if len(sys.argv) < 4:
            print("Verwendung: rewrite-add <domain> <ip>")
            return 1
        return cmd_rewrite_add(sys.argv[2], sys.argv[3])
    elif cmd in ("rewrite-del", "rewrite-rm"):
        if len(sys.argv) < 3:
            print("Verwendung: rewrite-del <domain>")
            return 1
        return cmd_rewrite_del(sys.argv[2])
    elif cmd in ("blocks", "block-list"):
        return cmd_blocks_list()
    elif cmd in ("block",):
        if len(sys.argv) < 3:
            print("Verwendung: block <service>")
            return 1
        return cmd_block(sys.argv[2])
    elif cmd in ("unblock",):
        if len(sys.argv) < 3:
            print("Verwendung: unblock <service>")
            return 1
        return cmd_unblock(sys.argv[2])
    elif cmd in ("whitelist-add",):
        if len(sys.argv) < 3:
            print("Verwendung: whitelist-add <domain>")
            return 1
        return cmd_whitelist_add(sys.argv[2])
    elif cmd in ("whitelist-del", "whitelist-rm"):
        if len(sys.argv) < 3:
            print("Verwendung: whitelist-del <domain>")
            return 1
        return cmd_whitelist_del(sys.argv[2])
    elif cmd in ("upstream",):
        if len(sys.argv) < 3:
            print("Verwendung: upstream <dns1> [dns2] ...")
            return 1
        return cmd_upstream_set(sys.argv[2:])
    elif cmd in ("help", "-h", "--help"):
        usage()
        return 0
    else:
        print("Unbekannter Befehl: '{}'".format(cmd))
        usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Nmap Output Reference

## Port States

| State | Meaning |
|-------|---------|
| `open` | Port is actively accepting connections |
| `closed` | Port is reachable but no service listening |
| `filtered` | Nmap cannot determine if open (firewall dropping packets) |
| `open\|filtered` | Can't distinguish between open and filtered (UDP scans) |
| `unfiltered` | Reachable but can't determine open/closed (ACK scan) |

## Version Output Fields

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd 2.4.51 ((Debian))
22/tcp   open  ssh     OpenSSH 8.4p1 Debian 5+deb11u1 (protocol 2.0)
```

- **PORT**: Port number and protocol
- **STATE**: Port state (see above)
- **SERVICE**: Service name from `/etc/services` or nmap's database
- **VERSION**: Banner / detected version string (with `-sV`)

## OS Detection Output

```
OS details: Linux 4.15 - 5.6
Network Distance: 1 hop
```

OS detection requires at least one open and one closed TCP port. Confidence shown as `(100%)`.

## NSE Script Output

Scripts output under the port they tested:

```
80/tcp open  http
| http-title:
|   Title: Apache2 Debian Default Page
|_  Requested resource was http://192.168.1.1/
| http-methods:
|   Supported Methods: OPTIONS GET POST
|_  Potentially risky methods: OPTIONS
```

## Grepable Format Fields

Fields in `-oG` output:
- `Host: IP (hostname)` — target host
- `Ports: port/state/proto/owner/service/rpc/version` — port details
- `OS: os_string` — OS guess

Parse open ports:
```bash
grep "Status: Up" scan.gnmap | awk '{print $2}'
grep "Ports:" scan.gnmap | grep -oP '\d+/open/tcp'
```

## XML Output Parsing

```bash
# Extract open ports with xmllint
xmllint --xpath "//port[@protocol='tcp'][state/@state='open']/@portid" scan.xml

# With Python
python3 - <<'EOF'
import xml.etree.ElementTree as ET
tree = ET.parse('scan.xml')
for port in tree.findall(".//port"):
    if port.find('state').get('state') == 'open':
        print(f"{port.get('portid')}/{port.get('protocol')}")
EOF
```

## Common Service Ports

| Port | Service |
|------|---------|
| 21 | FTP |
| 22 | SSH |
| 23 | Telnet |
| 25 | SMTP |
| 53 | DNS |
| 80 | HTTP |
| 110 | POP3 |
| 143 | IMAP |
| 443 | HTTPS |
| 445 | SMB |
| 3306 | MySQL |
| 3389 | RDP |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 8080 | HTTP Alternate |
| 8443 | HTTPS Alternate |
| 27017 | MongoDB |

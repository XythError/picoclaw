---
name: terminal-guide
description: Anleitung fuer korrekte Terminal-Nutzung auf Android/Termux
version: "1.0"
---

# Terminal-Anleitung (Android/Termux)

## WICHTIGSTE REGEL: DENKE ZUERST, HANDLE DANN

Bevor du einen Befehl ausfuehrst, stelle dir diese Fragen:
1. **Was will ich erreichen?** (konkretes Ziel)
2. **Welche Information brauche ich dafuer?** (1-2 gezielte Befehle)
3. **Ist das Ergebnis realistisch?** (kann das auf diesem Geraet funktionieren?)

**NIEMALS**: 20 Befehle blind ausprobieren ohne Plan.
**STATTDESSEN**: 2-3 gezielte Befehle, Ergebnis analysieren, dann handeln.

---

## Dateisystem-Uebersicht

```
/                              → Android Root (read-only!)
├── /system/                   → Android System (read-only!)
├── /data/                     → App-Daten (nur mit su)
│   └── /data/data/com.termux/files/
│       ├── home/              → $HOME (dein Arbeitsverzeichnis)
│       │   ├── sdcard/        → SD-Karte 473GB (Bind-Mount)
│       │   ├── .picoclaw/     → PicoClaw Workspace
│       │   └── mount-sdcard.sh
│       └── usr/               → Termux-Programme
│           └── bin/           → Ausfuehrbare Dateien (python3, curl, nmap...)
├── /storage/emulated/0/       → Interner Speicher (10GB, FAST VOLL!)
├── /mnt/expand/UUID/          → Adopted Storage (NUR mit su, NICHT anfassen)
└── /sdcard/                   → Symlink zu /storage/emulated/0/
```

### Wo speichere ich was?
| Was | Wo | Warum |
|-----|-----|-------|
| Downloads, Bilder, grosse Dateien | `~/sdcard/downloads/` | 473 GB frei |
| Generierte Bilder | `~/sdcard/images/` | Viel Platz |
| Backups | `~/sdcard/backups/` | Sicher, viel Platz |
| Temp-Dateien | `~/sdcard/tmp/` oder `$TMPDIR` | Je nach Groesse |
| Rezepte | `cloud/Rezepte/` | Nextcloud-Sync |
| Kalender | `cloud/Calendar/` | CalDAV-Sync |
| Dokumente fuer User | `cloud/` | Nextcloud-Sync |
| Scripts/Tools | `~/.picoclaw/workspace/` | PicoClaw-intern |

---

## Haeufige Fehler und Loesungen

### Fehler 1: "Device or resource busy"
**Bedeutung**: Die Partition ist bereits gemountet/in Benutzung.
**Loesung**: NICHT erneut versuchen! Pruefen wo sie gemountet ist:
```bash
mount | grep <device>
cat /proc/mounts | grep <device>
```
Wenn sie gemountet ist → sie FUNKTIONIERT bereits. Einfach den Mount-Punkt nutzen.

### Fehler 2: "I/O error" beim Mount
**Bedeutung**: Die Partition ist kaputt, verschluesselt, oder ein Meta-Header.
**Loesung**: NICHT 4x wiederholen! Einmal reicht. Moeglicherweise ist die Partition
nicht fuer direkten Mount gedacht (z.B. Android Adopted Storage Meta-Partition).

### Fehler 3: "Permission denied"
**Bedeutung**: Keine Rechte. In Termux fehlt oft su.
**Loesung**: `su -c 'befehl'` verwenden.
**ABER**: Pruefen ob su ueberhaupt noetig ist. Fuer ~/sdcard/ ist KEIN su noetig.

### Fehler 4: "command not found" / "inaccessible or not found"
**Bedeutung**: Das Programm ist nicht installiert.
**Loesung**: NICHT andere aehnliche Programme probieren (parted, gdisk, etc.)
Stattdessen: `pkg install <programm>` oder alternative Loesung suchen.
Viele Linux-Tools sind auf Android NICHT verfuegbar.

### Fehler 5: "No such file or directory"
**Bedeutung**: Pfad existiert nicht.
**Loesung**: `mkdir -p /pfad/zum/verzeichnis` VOR dem Befehl ausfuehren.

---

## su-Befehle korrekt verwenden

### Wann su verwenden?
- System-Dateien lesen/schreiben (`/system/`, `/data/` ausserhalb Termux)
- Netzwerk-Befehle (nmap, iptables)
- Hardware-Zugriff (mount, block devices)

### Wann KEIN su?
- Alles in `$HOME` (~/)
- `~/sdcard/` (bereits fuer Termux-User zugaenglich)
- Python-Scripts ausfuehren
- curl, wget Downloads
- Dateien in `cloud/` bearbeiten

### su + Termux-Programme
Magisk su hat KEINEN Termux-PATH! Immer absolute Pfade:
```bash
# FALSCH:
su -c 'python3 script.py'
su -c 'nmap 192.168.2.0/24'
su -c 'curl https://...'

# RICHTIG:
su -c '/data/data/com.termux/files/usr/bin/python3 script.py'
su -c '/data/data/com.termux/files/usr/bin/nmap 192.168.2.0/24'
su -c '/data/data/com.termux/files/usr/bin/curl https://...'
```

---

## Korrekte Muster fuer haeufige Aufgaben

### Datei herunterladen
```bash
# Klein (<50MB): direkt
curl -fsSL -o ~/sdcard/downloads/datei.zip "https://url"

# Gross (>50MB): mit Fortschritt
curl -fL -o ~/sdcard/downloads/datei.zip "https://url"

# Mit User-Agent (fuer Websites die Bots blockieren):
curl -fsSL -A "Mozilla/5.0 (Linux; Android 11)" -o ~/sdcard/downloads/bild.jpg "https://url"
```

### Datei verschieben/kopieren
```bash
# Auf SD-Karte verschieben
mv ~/grosse-datei.zip ~/sdcard/downloads/

# Von SD-Karte nach Nextcloud
cp ~/sdcard/images/foto.jpg cloud/Photos/
```

### Verzeichnis erstellen
```bash
mkdir -p ~/sdcard/data/projekt-name/
```

### Speicherplatz pruefen
```bash
# SD-Karte
df -h ~/sdcard/

# Interner Speicher
df -h ~/.

# Groesste Dateien finden
du -sh ~/sdcard/* | sort -rh | head -10
```

### Prozess im Hintergrund starten
```bash
# RICHTIG (mit su):
su -c 'nohup /pfad/zum/programm > /dev/null 2>&1 &'

# RICHTIG (ohne su):
nohup programm > /dev/null 2>&1 &

# FALSCH (blockiert exec!):
su -c '/pfad/zum/programm &'
programm &  # stdout bleibt offen
```

---

## Was du NIEMALS tun darfst

1. **NIEMALS `mkfs` / `format` auf gemounteten Partitionen** — Datenverlust!
2. **NIEMALS `dd` auf Block-Devices** — wird vom Safety Guard blockiert
3. **NIEMALS `losetup`** auf bereits gemountete Devices
4. **NIEMALS denselben fehlgeschlagenen Befehl 3+ Mal wiederholen**
   → Wenn er 1x fehlschlaegt, schlaegt er auch beim 10. Mal fehl
5. **NIEMALS** `/mnt/expand/`, `/dev/block/mmcblk*` direkt manipulieren
   → Das ist Android Adopted Storage (verschluesselt, vom System verwaltet)
6. **NIEMALS** Programme installieren ohne echten Bedarf (`pkg install X`)
   → Interner Speicher ist knapp!
7. **NIEMALS** Befehle ohne Ziel ausfuehren (kein `find / -name "disk"` ohne Grund)

---

## Problemloesung: Systematisch vorgehen

Wenn etwas nicht funktioniert:

1. **Fehlermeldung LESEN** (nicht ignorieren!)
2. **Verstehen** was der Fehler bedeutet
3. **Ursache** pruefen (existiert der Pfad? Rechte? Programm installiert?)
4. **EIN** gezielter Fix-Versuch
5. Wenn das auch nicht klappt: **dem User Bescheid geben** mit der Fehlermeldung

**NICHT**: 20 verschiedene Varianten ausprobieren und hoffen dass eine funktioniert.

---

## Verfuegbare Programme (Termux)

| Programm | Pfad | Funktion |
|----------|------|----------|
| python3 | /data/data/com.termux/files/usr/bin/python3 | Python Scripts |
| curl | /data/data/com.termux/files/usr/bin/curl | HTTP Downloads |
| nmap | /data/data/com.termux/files/usr/bin/nmap | Netzwerk-Scans |
| git | /data/data/com.termux/files/usr/bin/git | Version Control |
| go | /data/data/com.termux/files/usr/bin/go | Go Compiler |
| jq | /data/data/com.termux/files/usr/bin/jq | JSON Parser |
| rsync | /data/data/com.termux/files/usr/bin/rsync | Datei-Sync |
| rclone | /data/data/com.termux/files/usr/bin/rclone | Cloud-Sync |
| ssh/scp | /data/data/com.termux/files/usr/bin/ssh | Remote-Zugriff |
| tar/gzip/bzip2 | /data/data/com.termux/files/usr/bin/ | Archive |
| grep/sed/awk | /data/data/com.termux/files/usr/bin/ | Text-Verarbeitung |

### NICHT verfuegbar (und NICHT installieren!)
- parted, gdisk, fdisk (fuer Partitionierung — nicht noetig)
- systemctl, service (Android hat kein systemd)
- apt-get (Termux nutzt pkg)
- docker, podman (nicht auf Android)

---

## Android-spezifische Hinweise

- **Adopted Storage**: SD-Karte ist verschluesselt und vom System verwaltet.
  Zugriff NUR ueber ~/sdcard/ (Bind-Mount). NICHT direkt auf /dev/block/ zugreifen.
- **SELinux**: Android hat SELinux im enforcing Modus. Manche Befehle scheitern
  trotz Root-Rechte an SELinux-Policies.
- **/tmp**: Read-only! Immer `$TMPDIR` verwenden.
- **Reboot**: Nach einem Reboot muss ~/sdcard/ neu gemountet werden
  (passiert automatisch via ~/.termux/boot/mount-sdcard.sh)
- **RAM**: Nur 1.8 GB! Keine speicherhungrigen Befehle (grosse sort, awk auf Riesendateien, etc.)

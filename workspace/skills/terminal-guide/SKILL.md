---
name: terminal-guide
description: "Reference guide for terminal and shell usage. Use when the user needs help with shell commands, scripting, navigation, file operations, pipes, redirects, process management, or general command-line productivity tips."
metadata: {"nanobot":{"emoji":"🖥️","os":["darwin","linux"]}}
---

# Terminal Guide

Quick reference for shell commands and productivity patterns.

## Navigation

```bash
cd ~            # Home directory
cd -            # Previous directory
pwd             # Print working directory
ls -lah         # Long list, all files, human-readable sizes
tree -L 2       # Directory tree, 2 levels deep
```

## File Operations

```bash
cp -r src/ dst/          # Copy directory recursively
mv old.txt new.txt       # Move / rename
rm -rf dir/              # Remove directory (caution!)
mkdir -p a/b/c           # Create nested directories
touch file.txt           # Create empty file / update timestamp
ln -s target link        # Create symbolic link
```

## Search

```bash
find . -name "*.log" -mtime -7      # Files modified last 7 days
grep -r "pattern" ./src --include="*.go"
grep -n "TODO" *.py                 # Show line numbers
rg "pattern" --type js              # ripgrep (faster)
```

## Pipes & Redirects

```bash
cmd | head -20           # First 20 lines
cmd | tail -f log.txt    # Follow live log output
cmd > out.txt            # Redirect stdout to file (overwrite)
cmd >> out.txt           # Append stdout to file
cmd 2>&1 | tee out.txt   # Capture stdout+stderr, show and save
cmd 2>/dev/null          # Discard errors
```

## Process Management

```bash
ps aux | grep python     # Find process by name
kill -9 PID              # Force kill process
pkill -f "pattern"       # Kill by name pattern
jobs                     # List background jobs
bg %1                    # Resume job in background
fg %1                    # Bring job to foreground
nohup cmd &              # Run detached, immune to hangup
```

## Text Processing

```bash
sort -k2 -n file.txt     # Sort by 2nd column numerically
uniq -c                  # Count duplicate lines
wc -l file.txt           # Line count
cut -d',' -f1,3 file.csv # Extract CSV columns 1 and 3
awk '{print $2}' file    # Print second field
sed 's/old/new/g' file   # Replace all occurrences
```

## Compression

```bash
tar czf archive.tar.gz dir/    # Create gzipped archive
tar xzf archive.tar.gz         # Extract gzipped archive
zip -r archive.zip dir/        # Create zip
unzip archive.zip -d ./out/    # Extract zip
```

## Networking

```bash
curl -s "https://api.example.com" | jq .
curl -X POST -H "Content-Type: application/json" -d '{"key":"val"}' URL
wget -q -O /tmp/file.txt URL
nc -zv host 443                # TCP connectivity check
ss -tlnp                       # Show listening ports
```

## Useful Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Kill current process |
| `Ctrl+Z` | Suspend current process |
| `Ctrl+D` | Exit / EOF |
| `Ctrl+R` | Reverse history search |
| `Ctrl+L` | Clear screen |
| `!!` | Repeat last command |
| `!$` | Last argument of previous command |
| `Alt+.` | Insert last argument of previous command |

## Advanced Patterns

See `references/advanced-shell.md` for:
- Shell scripting (variables, loops, conditionals)
- Functions and aliases
- Environment variable management
- Shell options (`set -euo pipefail`)
- Here documents and process substitution

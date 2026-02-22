# Advanced Shell Reference

## Variables & Parameter Expansion

```bash
name="World"
echo "Hello, ${name}!"
echo "${name:-default}"        # Use default if unset
echo "${name:=default}"        # Assign default if unset
echo "${#name}"                # Length of variable
echo "${name^^}"               # Uppercase (bash 4+)
echo "${name/World/Shell}"     # Replace first occurrence
echo "${name//l/L}"            # Replace all occurrences
```

## Arrays

```bash
arr=("a" "b" "c")
echo "${arr[0]}"               # First element
echo "${arr[@]}"               # All elements
echo "${#arr[@]}"              # Array length
arr+=("d")                     # Append
for item in "${arr[@]}"; do echo "$item"; done
```

## Conditionals

```bash
if [[ -f file.txt ]]; then
  echo "file exists"
elif [[ -d dir/ ]]; then
  echo "directory exists"
else
  echo "neither"
fi

# Common test flags
# -f  regular file    -d  directory    -e  exists
# -z  zero-length     -n  non-empty    -r  readable
# -x  executable      -s  non-empty file

[[ "$var" == "value" ]] && echo "match"
[[ "$var" =~ ^[0-9]+$ ]] && echo "numeric"
```

## Loops

```bash
# For loop over list
for i in 1 2 3 4 5; do echo "$i"; done

# For loop over files
for f in *.txt; do echo "$f"; done

# C-style for loop
for ((i=0; i<10; i++)); do echo "$i"; done

# While loop
while IFS= read -r line; do
  echo "$line"
done < file.txt

# Until loop
until ping -c1 host &>/dev/null; do
  sleep 5
done
```

## Functions

```bash
greet() {
  local name="${1:-World}"
  echo "Hello, ${name}!"
  return 0
}
greet "Alice"

# Functions with error handling
safe_rm() {
  if [[ -z "$1" ]]; then
    echo "Error: no argument" >&2
    return 1
  fi
  rm -rf "$1"
}
```

## Shell Options (Robust Scripts)

Always add at the top of scripts:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# set -e  exit on error
# set -u  treat unset variables as errors
# set -o pipefail  pipe fails if any command fails
```

## Aliases (in ~/.bashrc or ~/.zshrc)

```bash
alias ll='ls -lah'
alias gs='git status'
alias gp='git push'
alias ..='cd ..'
alias ...='cd ../..'
```

## Environment Variables

```bash
export MY_VAR="value"          # Set for current session and subprocesses
unset MY_VAR                   # Remove variable
env | grep MY_VAR              # Check value
printenv MY_VAR                # Print single variable

# Persistent: add to ~/.bashrc or ~/.zshrc
echo 'export MY_VAR="value"' >> ~/.bashrc
source ~/.bashrc
```

## Here Documents

```bash
cat <<EOF > config.txt
server = localhost
port = 8080
EOF

# No variable expansion with quoted delimiter
cat <<'EOF'
The $HOME variable will not be expanded here.
EOF
```

## Process Substitution

```bash
diff <(sort file1.txt) <(sort file2.txt)   # Diff sorted versions
while IFS= read -r line; do
  echo "$line"
done < <(find . -name "*.log")
```

## Signal Trapping

```bash
cleanup() {
  echo "Cleaning up..."
  rm -f /tmp/myapp.lock
}
trap cleanup EXIT INT TERM
```

## Job Control

```bash
cmd &                   # Run in background
wait                    # Wait for all background jobs
wait $!                 # Wait for last background job
{ cmd1; cmd2; } &       # Run group in background
```

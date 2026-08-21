# Bash & Shell Scripting — CKAD

> POSIX sh for inside pods (alpine/busybox), bash for the exam terminal.
> ponytail: shortest correct form first.

## sh vs bash — know what works where

| Feature | sh (POSIX) | bash |
|---------|:---:|:---:|
| `[ ]` test | ✅ | ✅ |
| `[[ ]]` extended test | ❌ | ✅ |
| Arrays `()` | ❌ | ✅ |
| `${var//find/replace}` | ❌ | ✅ |
| `&>/dev/null` | ❌ | ✅ (`>/dev/null 2>&1`) |
| `$()` subshell | ✅ | ✅ |
| Here-strings `<<<` | ❌ | ✅ |
| `{1..10}` brace expansion | ❌ | ✅ |
| `local` in functions | ⚠️ (common but not POSIX) | ✅ |

**Rule**: Inside `kubectl exec` → assume sh. Exam terminal → bash.

## One-liners (exam speed)

```bash
# Repeat command until success
while ! curl -s http://svc:80; do sleep 1; done

# Watch resource changes
watch -n1 kubectl get pods

# Quick loop over items
for p in $(k get pods -o name); do k delete "$p" --force --grace-period 0; done

# Generate sequence (bash)
for i in {1..5}; do echo "pod-$i"; done

# Generate sequence (sh/POSIX)
i=1; while [ $i -le 5 ]; do echo "pod-$i"; i=$((i+1)); done

# Find and kill by pattern
k get pods | grep Error | awk '{print $1}' | xargs kubectl delete pod $now

# Quick file from stdin
cat <<EOF > /tmp/test.yaml
apiVersion: v1
kind: Pod
metadata:
  name: test
EOF

# Conditional with short-circuit
[ -f /tmp/ready ] && echo "ready" || echo "not ready"
```

## Variables & parameter expansion

```bash
name="hello-world"
echo "${name}"            # hello-world
echo "${name^^}"          # HELLO-WORLD (bash only)
echo "${name%%-*}"        # hello (remove longest suffix match)
echo "${name#*-}"         # world (remove shortest prefix match)
echo "${name:-default}"   # use default if unset/empty
echo "${name:+exists}"    # print "exists" only if name is set

# Assign default
: "${PORT:=8080}"         # sets PORT=8080 if unset
```

## Conditionals

```bash
# POSIX (works everywhere)
if [ -z "$VAR" ]; then echo "empty"; fi
if [ "$A" = "$B" ]; then echo "equal"; fi
if [ -f /path/file ]; then echo "exists"; fi
if [ -d /path/dir ]; then echo "is dir"; fi

# bash-only (more readable, safer)
if [[ -z "$VAR" ]]; then echo "empty"; fi
if [[ "$A" == "$B" ]]; then echo "equal"; fi
if [[ "$A" =~ ^[0-9]+$ ]]; then echo "is number"; fi  # regex

# Numeric comparison
if [ "$count" -gt 5 ]; then echo "big"; fi
if (( count > 5 )); then echo "big"; fi  # bash arithmetic
```

## Test operators

| Operator | Meaning |
|----------|---------|
| `-z "$s"` | String is empty |
| `-n "$s"` | String is non-empty |
| `-f path` | File exists |
| `-d path` | Directory exists |
| `-x path` | File is executable |
| `-eq -ne -lt -gt -le -ge` | Numeric comparison |
| `=` / `!=` | String comparison (in `[ ]`) |
| `==` / `!=` | String comparison (in `[[ ]]`) |

## Loops

```bash
# Iterate list
for item in a b c; do echo "$item"; done

# Iterate command output
for pod in $(kubectl get pods -o name); do
  kubectl logs "$pod" --tail=5
done

# While read (line-safe, handles spaces)
kubectl get pods -o name | while read -r pod; do
  echo "checking $pod"
done

# C-style (bash only)
for ((i=0; i<10; i++)); do echo "$i"; done

# Infinite loop with break
while true; do
  result=$(curl -s http://svc/health)
  [ "$result" = "ok" ] && break
  sleep 2
done
```

## Functions (reusable patterns)

```bash
# POSIX function
log() { echo "[$(date +%H:%M:%S)] $*"; }

# With return code
check_ready() {
  kubectl get pod "$1" -o jsonpath='{.status.phase}' 2>/dev/null | grep -q Running
}

# Usage
if check_ready nginx; then
  log "nginx is running"
fi

# Retry pattern
retry() {
  local n="${1:-3}" cmd="${*:2}"
  for i in $(seq 1 "$n"); do
    eval "$cmd" && return 0
    sleep 1
  done
  return 1
}
retry 5 curl -s http://svc:80/health
```

## Pipes, redirects & process substitution

```bash
# Redirect
cmd > out.txt 2>&1         # stdout+stderr to file
cmd >> out.txt             # append
cmd 2>/dev/null            # discard errors
cmd < input.txt            # stdin from file

# Pipes
k get pods | grep -v Running | awk 'NR>1{print $1}'

# Process substitution (bash only) — compare two outputs
diff <(k get pods -n ns1) <(k get pods -n ns2)

# tee — write to file AND stdout
k get pods | tee /tmp/pods.txt

# xargs — parallel execution
echo "pod1 pod2 pod3" | xargs -n1 kubectl delete pod
```

## Text processing (exam essentials)

```bash
# grep
grep -r "pattern" /path/          # recursive search
grep -c "Error" log.txt           # count matches
grep -v "Running"                 # invert (exclude)
grep -E "pat1|pat2"               # extended regex (OR)

# awk
awk '{print $1}'                  # first column
awk -F: '{print $1}'              # custom delimiter
awk 'NR>1{print $1}'             # skip header

# sed
sed 's/old/new/' file             # first occurrence per line
sed 's/old/new/g' file            # all occurrences
sed -i 's/old/new/g' file         # in-place edit
sed -n '5,10p' file               # print lines 5-10

# cut
echo "a:b:c" | cut -d: -f2       # → b

# sort + uniq
k get pods -o jsonpath='{.items[*].spec.nodeName}' | tr ' ' '\n' | sort | uniq -c

# jq (if available)
k get pod nginx -o json | jq '.status.phase'
```

## jsonpath & custom-columns (CKAD essential)

```bash
# Single field
k get pod nginx -o jsonpath='{.status.podIP}'

# Multiple fields
k get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'

# Custom columns (readable table)
k get pods -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,IP:.status.podIP'

# Filter by condition
k get pods -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'
```

## Debugging in pods

```bash
# Shell into running pod
k exec -it nginx -- sh          # sh (always available)
k exec -it nginx -- bash        # bash (only if installed)

# Check connectivity from inside
wget -qO- http://svc:80        # alpine/busybox (no curl)
curl -s http://svc:80          # if curl installed

# DNS check
nslookup svc.namespace.svc.cluster.local
cat /etc/resolv.conf

# Check env vars injected
env | grep -i secret
env | sort

# Check mounted volumes
ls -la /path/to/mount
cat /path/to/mount/config-key
```

## Script patterns (legible & reusable)

```bash
#!/usr/bin/env bash
set -euo pipefail
# -e: exit on error
# -u: error on undefined variable
# -o pipefail: pipe fails if any command fails

# Constants at the top
readonly NAMESPACE="production"
readonly TIMEOUT=30

# Functions before main logic
die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[$(date +%T)] $*"; }

# Input validation
[ $# -lt 1 ] && die "Usage: $0 <pod-name>"

# Main logic
main() {
  local pod="$1"
  log "Checking $pod in $NAMESPACE"
  kubectl get pod "$pod" -n "$NAMESPACE" || die "Pod $pod not found"
}

main "$@"
```

## Traps & cleanup

```bash
cleanup() { rm -f /tmp/scratch.*; }
trap cleanup EXIT          # runs on script exit (success or failure)
trap 'echo interrupted' INT  # Ctrl+C handler
```

## Useful exam aliases (add to ~/.bashrc)

```bash
alias k=kubectl
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kgd='kubectl get deploy'
alias kd='kubectl describe'
alias kaf='kubectl apply -f'
alias kdf='kubectl delete -f'
export do="--dry-run=client -o yaml"
export now="--force --grace-period 0"
```

## Quick reference: exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Misuse of shell builtin |
| 126 | Command not executable |
| 127 | Command not found |
| 128+N | Killed by signal N |
| 130 | Ctrl+C (SIGINT) |

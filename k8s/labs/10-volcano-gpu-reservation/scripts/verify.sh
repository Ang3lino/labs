#!/usr/bin/env bash
# Pass/fail check for the reservation mechanism. Run after step 4.
set -uo pipefail

pass=0; fail=0
check() { # name, actual, expected
  if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1))
  else echo "  FAIL  $1 (got '$2', want '$3')"; fail=$((fail+1)); fi
}

echo "== reservation verification =="

check "reserved job is Running" \
  "$(kubectl get pod reserved-claim-0 -o jsonpath='{.status.phase}' 2>/dev/null)" \
  "Running"

check "reservation queue is not reclaimable" \
  "$(kubectl get queue reserved-team-a -o jsonpath='{.spec.reclaimable}' 2>/dev/null)" \
  "false"

check "reserved capacity is 2 p2p GPUs" \
  "$(kubectl get queue reserved-team-a -o jsonpath='{.spec.deserved.apex\.io/gpu-p2p}' 2>/dev/null)" \
  "2"

check "shared queue cannot touch p2p GPUs" \
  "$(kubectl get queue shared -o jsonpath='{.spec.capability.apex\.io/gpu-p2p}' 2>/dev/null)" \
  ""

expires="$(kubectl get queue reserved-team-a -o jsonpath='{.metadata.annotations.apex\.io/expires-at}' 2>/dev/null)"
check "reservation carries an expiry annotation" \
  "$([ -n "$expires" ] && echo yes || echo no)" \
  "yes"

echo
echo "queues:"; kubectl get queues 2>/dev/null
echo
echo "pods by queue:"
kubectl get pods -l queue -L queue --no-headers 2>/dev/null \
  | awk '{printf "  %-20s %-10s queue=%s\n", $1, $3, $6}'
echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
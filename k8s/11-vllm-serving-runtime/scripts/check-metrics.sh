#!/usr/bin/env bash
# Criterion C5: do the three metrics the platform depends on actually exist?
# Run against a port-forwarded vLLM: kubectl port-forward svc/vllm 8000:8000
set -uo pipefail
BASE="${BASE:-http://localhost:8000}"

metrics="$(curl -sf "$BASE/metrics" || true)"
if [ -z "$metrics" ]; then
  echo "FAIL: no /metrics endpoint at $BASE"
  echo "      a runtime without one means you build metrics yourself (see: TensorRT-LLM)"
  exit 1
fi

pass=0; fail=0
want() {
  if echo "$metrics" | grep -q "^$1"; then
    echo "  PASS  $1"
    echo "$metrics" | grep "^$1" | head -1 | sed 's/^/          /'
    pass=$((pass+1))
  else
    echo "  FAIL  $1  <- $2"
    fail=$((fail+1))
  fi
}

echo "== C5: required metrics =="
want "vllm:time_to_first_token_seconds"  "no TTFT means no latency SLO"
want "vllm:num_requests_waiting"         "no queue depth means autoscaling on the wrong signal"
want "vllm:gpu_cache_usage_perc"         "no KV cache visibility means no capacity planning"

echo
echo "== also present =="
echo "$metrics" | grep -E '^# HELP vllm' | sed 's/^# HELP /  /' | head -20

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
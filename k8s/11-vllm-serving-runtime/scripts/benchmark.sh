#!/usr/bin/env bash
# Part C (GPU): TP=1 vs TP=2 head-to-head. The comparison that decides whether
# tensor parallelism is buying you anything on this hardware.
set -uo pipefail
MODEL="${MODEL:-facebook/opt-1.3b}"
PROMPT='{"role":"user","content":"Explain tensor parallelism in three sentences."}'

echo "== interconnect topology =="
if command -v nvidia-smi >/dev/null; then
  nvidia-smi topo -m || true
  echo
  echo "PIX/PXB = peer-to-peer over PCIe. SYS = through host RAM (abandon TP=2)."
  echo "NV# = NVLink. L40S never shows NVLink - the card does not support it."
else
  echo "no nvidia-smi - this script needs a GPU node"
  exit 1
fi

bench() { # name, base-url
  local name="$1" base="$2"
  echo
  echo "== $name =="
  local t0 t1
  t0=$(date +%s.%N)
  for _ in $(seq 1 5); do
    curl -sf "$base/v1/chat/completions" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$MODEL\",\"messages\":[$PROMPT],\"max_tokens\":128}" \
      -o /dev/null
  done
  t1=$(date +%s.%N)
  echo "  5 sequential requests: $(echo "$t1 - $t0" | bc)s"
  curl -sf "$base/metrics" | grep -E '^vllm:(time_to_first_token_seconds_sum|gpu_cache_usage_perc)' | sed 's/^/  /'
}

# kubectl port-forward svc/vllm-gpu-tp1 8001:8000 &
# kubectl port-forward svc/vllm-gpu-tp2 8002:8000 &
bench "TP=1 (one replica per GPU)" "${TP1:-http://localhost:8001}"
bench "TP=2 (one replica across two GPUs)" "${TP2:-http://localhost:8002}"

echo
echo "Expect TP=2 to be SLOWER per request on PCIe-only hardware."
echo "TP=2 is a capacity mechanism for models that do not fit on one card,"
echo "not a latency optimisation. If the model fits at TP=1, use TP=1."
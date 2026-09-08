#!/usr/bin/env bash
# Criterion C2: watch continuous batching. Fire N concurrent requests and read
# num_requests_running - it should exceed 1, meaning several sequences are
# generating in the SAME forward pass.
set -uo pipefail
N="${1:-20}"
BASE="${BASE:-http://localhost:8000}"
MODEL="${MODEL:-facebook/opt-125m}"

echo "firing $N concurrent requests at $BASE"
for i in $(seq 1 "$N"); do
  curl -sf "$BASE/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"write a short poem number $i\"}],\"max_tokens\":64}" \
    -o /dev/null &
done

sleep 3
echo
echo "== batching state while in flight =="
curl -sf "$BASE/metrics" | grep -E '^vllm:num_requests_(running|waiting)' || echo "  (no metrics)"

wait
echo
echo "== after drain =="
curl -sf "$BASE/metrics" | grep -E '^vllm:num_requests_(running|waiting)' || true
echo
echo "num_requests_running > 1 while in flight == continuous batching is real."
echo "With static batching, a finished sequence leaves its slot idle until the"
echo "whole batch drains. Here a queued request takes it at the next token step."
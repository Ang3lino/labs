#!/bin/bash
set -e

# Usage: ./test-openai-surface.sh <HOST:PORT>
# opt-125m is a base completion model (no chat template) — tests use /v1/completions.
# Swap MODEL for an instruction-tuned model to exercise /v1/chat/completions instead.
HOST_PORT=${1:-"localhost:8000"}
MODEL="facebook/opt-125m"

echo "=== C4: Models Endpoint (OpenAI surface) ==="
curl -s http://${HOST_PORT}/v1/models | jq '.data[0] | {id, object, max_model_len}'

echo -e "\n=== C4: Completions (Non-Streaming) ==="
curl -s http://${HOST_PORT}/v1/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"prompt\": \"Kubernetes is\",
    \"max_tokens\": 20
  }" | jq '{id, model, choices: [.choices[0] | {text, finish_reason}]}'

echo -e "\n=== C3: Completions (Streaming / SSE) ==="
curl -N -s http://${HOST_PORT}/v1/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"prompt\": \"One two three\",
    \"max_tokens\": 20,
    \"stream\": true
  }" | grep "^data:" | grep -v "\[DONE\]" | head -5 | jq -r '.choices[0].text' 2>/dev/null | tr -d '\n'
echo -e "\n\n=== C5: Prometheus Metrics (queue depth + TTFT) ==="
curl -s http://${HOST_PORT}/metrics | grep -E "vllm:e2e_request_latency|vllm:time_to_first_token|vllm:num_requests_waiting|vllm:gpu_cache_usage" | head -10

echo -e "\n=== Done ==="

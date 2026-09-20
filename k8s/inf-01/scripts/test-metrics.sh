#!/bin/bash
set -e

# Usage: ./test-metrics.sh <HOST:PORT>
HOST_PORT=${1:-"localhost:8000"}

echo "=== Fetching Metrics ==="
# We look for TTFT, queue depth, and KV cache usage
curl -s http://${HOST_PORT}/metrics | grep -E 'time_to_first_token|num_requests_waiting|gpu_cache_usage_perc' || echo "No matching metrics found. Are you testing the right endpoint?"

echo -e "\n=== All vLLM metrics (Head) ==="
curl -s http://${HOST_PORT}/metrics | grep -E '^# HELP vllm' | head -n 15

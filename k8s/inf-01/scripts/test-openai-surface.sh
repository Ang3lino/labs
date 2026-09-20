#!/bin/bash
set -e

# Wait for port-forwarding or service to be available. 
# Usage: ./test-openai-surface.sh <HOST:PORT>
HOST_PORT=${1:-"localhost:8000"}

echo "=== Testing Models Endpoint ==="
curl -s http://${HOST_PORT}/v1/models | jq .

echo -e "\n=== Testing Chat Completions (Non-Streaming) ==="
curl -s http://${HOST_PORT}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "facebook/opt-125m",
    "messages": [{"role": "user", "content": "What is Kubernetes?"}],
    "max_tokens": 20
  }' | jq .

echo -e "\n=== Testing Chat Completions (Streaming) ==="
curl -N -s http://${HOST_PORT}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "facebook/opt-125m",
    "messages": [{"role": "user", "content": "Count to five."}],
    "max_tokens": 20,
    "stream": true
  }'
echo -e "\n=== Done ==="

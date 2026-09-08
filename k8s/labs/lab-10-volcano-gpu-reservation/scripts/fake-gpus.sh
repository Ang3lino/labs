#!/usr/bin/env bash
# Advertise fake GPUs as extended resources on the first node.
#
# Extended resources are just integers on Node.status.capacity, patchable via the
# API. No device plugin, no CUDA, no GPU. The scheduler accounts for them exactly
# as it would for nvidia.com/gpu, which is what makes this lab real.
#
# Two resources on purpose:
#   apex.io/gpu      - N cards, any of them, no topology promise
#   apex.io/gpu-p2p  - the 2 cards that can actually talk peer-to-peer
# Queue quota is scalar and topology-blind, so topology must live in the NAME.
set -euo pipefail

TOTAL="${1:-3}"
P2P="${2:-2}"
NODE="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"

echo "node: $NODE  ->  apex.io/gpu=$TOTAL, apex.io/gpu-p2p=$P2P"

# ~1 is the JSON-Pointer escape for the / inside the resource name.
kubectl patch node "$NODE" --subresource=status --type=json -p "$(cat <<JSON
[
  {"op": "add", "path": "/status/capacity/apex.io~1gpu", "value": "$TOTAL"},
  {"op": "add", "path": "/status/capacity/apex.io~1gpu-p2p", "value": "$P2P"}
]
JSON
)"

echo
echo "advertised capacity:"
echo "  apex.io/gpu      = $(kubectl get node "$NODE" -o jsonpath='{.status.capacity.apex\.io/gpu}')"
echo "  apex.io/gpu-p2p  = $(kubectl get node "$NODE" -o jsonpath='{.status.capacity.apex\.io/gpu-p2p}')"
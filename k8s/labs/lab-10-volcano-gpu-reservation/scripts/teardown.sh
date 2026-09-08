#!/usr/bin/env bash
# Remove everything this lab created. Volcano itself is left installed.
set -uo pipefail

kubectl delete -f "$(dirname "$0")/../manifests/" --ignore-not-found=true
kubectl delete job expiry-manual expiry-test --ignore-not-found=true
kubectl delete queue shared reserved-team-a --ignore-not-found=true

NODE="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
kubectl patch node "$NODE" --subresource=status --type=json -p '[
  {"op": "remove", "path": "/status/capacity/apex.io~1gpu"},
  {"op": "remove", "path": "/status/capacity/apex.io~1gpu-p2p"}
]' 2>/dev/null || echo "fake resources already gone"

echo "teardown complete. to remove Volcano itself:"
echo "  kubectl delete -f https://raw.githubusercontent.com/volcano-sh/volcano/v1.9.0/installer/volcano-development.yaml"
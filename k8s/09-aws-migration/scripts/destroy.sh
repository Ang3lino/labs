#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT_DIR}/terraform"
K8S_DIR="${ROOT_DIR}/k8s-aws"

kubectl delete -f "${K8S_DIR}/ingress.yaml" --ignore-not-found=true
kubectl delete -f "${K8S_DIR}/neo4j-statefulset.yaml" --ignore-not-found=true
kubectl delete -f "${K8S_DIR}/storageclass.yaml" --ignore-not-found=true

cd "${TF_DIR}"
terraform destroy -auto-approve

REGION="$(terraform output -raw region 2>/dev/null || echo us-east-1)"
for repo in graph-rag/ingestion graph-rag/rag-api infra-intel/graph-builder infra-intel/query-api; do
  IMAGE_IDS="$(aws ecr list-images --repository-name "${repo}" --region "${REGION}" --query 'imageIds[*]' --output json 2>/dev/null || echo '[]')"
  if [ "${IMAGE_IDS}" != "[]" ]; then
    aws ecr batch-delete-image --repository-name "${repo}" --region "${REGION}" --image-ids "${IMAGE_IDS}" >/dev/null || true
  fi
done

echo "Cleanup complete. Verify in AWS Console: ALB, EBS volumes, NAT Gateway, and ECR repos are gone."

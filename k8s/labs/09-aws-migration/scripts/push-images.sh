#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT_DIR}/terraform"

cd "${TF_DIR}"
REGION="$(terraform output -raw region)"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

MAP_JSON="$(terraform output -json ecr_repository_urls)"
ingestion_repo="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["graph-rag/ingestion"])' <<< "${MAP_JSON}")"
rag_repo="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["graph-rag/rag-api"])' <<< "${MAP_JSON}")"
builder_repo="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["infra-intel/graph-builder"])' <<< "${MAP_JSON}")"
query_repo="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["infra-intel/query-api"])' <<< "${MAP_JSON}")"

docker tag ml-lab-07-ingestion:latest "${ingestion_repo}:latest"
docker tag ml-lab-07-rag-api:latest "${rag_repo}:latest"
docker tag ml-lab-08-graph-builder:latest "${builder_repo}:latest"
docker tag ml-lab-08-query-api:latest "${query_repo}:latest"

docker push "${ingestion_repo}:latest"
docker push "${rag_repo}:latest"
docker push "${builder_repo}:latest"
docker push "${query_repo}:latest"

echo "Pushed all lab images to ECR."

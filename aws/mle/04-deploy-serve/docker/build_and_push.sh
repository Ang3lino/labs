#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ECR_REPO_URI>"
  exit 1
fi

ECR_REPO_URI="$1"
IMAGE_NAME="mle-lab-04-serve"
IMAGE_TAG="latest"
ACCOUNT_REGISTRY="${ECR_REPO_URI%%/*}"

docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
aws ecr get-login-password | docker login --username AWS --password-stdin "${ACCOUNT_REGISTRY}"
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${ECR_REPO_URI}:${IMAGE_TAG}"
docker push "${ECR_REPO_URI}:${IMAGE_TAG}"

echo "Pushed ${ECR_REPO_URI}:${IMAGE_TAG}"

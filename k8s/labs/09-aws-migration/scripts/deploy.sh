#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT_DIR}/terraform"
K8S_DIR="${ROOT_DIR}/k8s-aws"

cd "${TF_DIR}"
CLUSTER_NAME="$(terraform output -raw cluster_name)"
REGION="$(terraform output -raw region)"
aws eks update-kubeconfig --name "${CLUSTER_NAME}" --region "${REGION}"

kubectl create namespace graph-rag --dry-run=client -o yaml | kubectl apply -f -
kubectl -n graph-rag create secret generic neo4j-auth --from-literal=NEO4J_AUTH="${NEO4J_AUTH:-neo4j/please-change-me}" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.8.1/docs/install/v2_8_1_full.yaml"
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/ecr/?ref=release-1.35"
# ponytail: direct upstream manifests keep lab setup short and transparent.

kubectl apply -f "${K8S_DIR}/storageclass.yaml"
kubectl apply -f "${K8S_DIR}/neo4j-statefulset.yaml"
kubectl apply -f "${K8S_DIR}/ingress.yaml"

kubectl -n graph-rag wait --for=condition=ready pod -l app=neo4j --timeout=300s
kubectl -n graph-rag get pods

ALB_HOST="$(kubectl -n graph-rag get ingress graph-rag-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' || true)"
echo "ALB endpoint: ${ALB_HOST:-pending}"

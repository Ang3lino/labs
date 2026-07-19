# Lab 05: ML Pipeline as Microservices

## Scenario

Your ML system has 3 stages: text preprocessing, feature extraction, and inference. The monolith is becoming hard to change and scale. You split it into microservices that talk to each other by Kubernetes DNS service names.

## What You'll Learn

- Namespaces for workload isolation
- Service discovery with in-cluster DNS (`http://service-name:port`)
- ConfigMaps for shared runtime configuration
- Multi-service ML architecture with independent scaling
- Inter-service communication patterns inside K8s

## Prerequisites

- Labs 01–04 completed
- Docker Desktop with Kubernetes enabled
- `kubectl` configured to your local cluster

## Step-by-Step Instructions

1. Build all service images:

```bash
docker build -t ml-lab-05-preprocessor:latest ./preprocessor
docker build -t ml-lab-05-featurizer:latest ./featurizer
docker build -t ml-lab-05-inference:latest ./inference
```

2. Create namespace:

```bash
kubectl apply -f k8s/namespace.yaml
```

3. Deploy all services:

```bash
kubectl apply -f k8s/ -n ml-pipeline
kubectl get all -n ml-pipeline
```

4. Test pipeline end-to-end through inference service:

```bash
kubectl port-forward svc/inference 8080:8080 -n ml-pipeline
```

In another terminal:

```bash
curl -s -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"  Great latency and easy deployment!  "}'
```

5. Show DNS-based service-to-service calls:

- Inference calls `http://preprocessor:8080/preprocess`
- Inference calls `http://featurizer:8080/featurize`

6. Inspect logs to see flow across services:

```bash
kubectl logs deployment/inference -n ml-pipeline
kubectl logs deployment/preprocessor -n ml-pipeline
kubectl logs deployment/featurizer -n ml-pipeline
```

7. Scale preprocessor independently:

```bash
kubectl scale deployment preprocessor --replicas=3 -n ml-pipeline
kubectl get pods -n ml-pipeline
```

## Verification Steps

1. Confirm namespace-scoped resources exist:

```bash
kubectl get deploy,svc,configmap -n ml-pipeline
```

2. Confirm inference can still predict after scaling only preprocessor:

```bash
curl -s -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"service discovery works"}'
```

3. Validate in-cluster DNS names from pod config/logs:

```bash
kubectl describe deployment inference -n ml-pipeline
```

## Cleanup

```bash
kubectl delete -f k8s/ -n ml-pipeline
kubectl delete namespace ml-pipeline
```

## Interview Talking Points

I architect ML systems as microservices with K8s service discovery. Each component scales independently, and services communicate using DNS names rather than hardcoded IPs.

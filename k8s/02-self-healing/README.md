# Lab 02: Self-Healing Inference Server

## Scenario

Your ML inference server crashes randomly after processing ~50 requests (memory leak in preprocessing). Instead of getting paged at 3 AM, make K8s handle it.

## What You'll Learn

- Why a pod can be "Running" but still unusable
- `livenessProbe` for restart-on-bad-state
- `readinessProbe` for traffic gating
- Container lifecycle and restart behavior in Deployments
- How to inspect restart events and health failures

## Prerequisites

- Docker Desktop Kubernetes running
- `kubectl` access
- Lab 01 familiarity (build/apply/curl basics)

## Step-by-Step Instructions

1. Build the image:

   ```bash
   docker build -t ml-lab-02:latest .
   ```

2. Deploy WITHOUT probes first:

   ```bash
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/deployment-no-probes.yaml
   kubectl port-forward service/ml-self-healing 8080:8080
   ```

3. Hit `/predict` 60 times:

   ```bash
   for i in {1..60}; do
     curl -s -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d '{"features": [5.1, 3.5, 1.4, 0.2]}' > /dev/null
   done
   curl -i http://localhost:8080/health
   ```

   You should now get HTTP 500, and the pod stays broken because no liveness probe exists.

4. Replace with deployment WITH probes:

   ```bash
   kubectl delete -f k8s/deployment-no-probes.yaml
   kubectl apply -f k8s/deployment-with-probes.yaml
   ```

5. Hit `/predict` 60 times again:

   ```bash
   for i in {1..60}; do
     curl -s -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d '{"features": [5.1, 3.5, 1.4, 0.2]}' > /dev/null
   done
   kubectl get pods
   ```

   K8s detects failed liveness checks and restarts the container.

6. Inspect restart evidence:

   ```bash
   kubectl get pods
   kubectl describe pod <pod-name>
   ```

   Look for probe failures and restart events.

## Verification Steps

- Without probes: `/health` returns 500 and `RESTARTS` stays 0
- With probes: `RESTARTS` increments after degradation
- `kubectl describe pod` shows liveness probe failed events
- `GET /ready` returns 200 when pod is available for traffic

## Cleanup

```bash
kubectl delete -f k8s/deployment-with-probes.yaml --ignore-not-found
kubectl delete -f k8s/deployment-no-probes.yaml --ignore-not-found
kubectl delete -f k8s/service.yaml
docker rmi ml-lab-02:latest
```

## Interview Talking Points

I implement health checks so K8s auto-restarts degraded ML services. I understand liveness vs readiness probes.

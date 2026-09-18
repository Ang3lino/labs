# Lab 04: Zero-Downtime Model Updates

## Scenario

Your sentiment model v1 has 78% accuracy. You retrained it — v2 hits 91%. Deploy v2 while v1 handles live traffic. If v2 is worse in prod, rollback in seconds.

## What You'll Learn

- Rolling updates in Kubernetes Deployments
- Zero-downtime strategy tuning with `maxSurge` and `maxUnavailable`
- Fast rollback with deployment revision history
- Safe model version upgrades without interrupting inference traffic

## Prerequisites

- Labs 01–03 completed
- Docker Desktop with Kubernetes enabled
- `kubectl` configured to your local cluster

## Step-by-Step Instructions

1. Build both images:

```bash
docker build -f Dockerfile.v1 -t ml-lab-04:v1 . && docker build -f Dockerfile.v2 -t ml-lab-04:v2 .
```

2. Deploy v1:

```bash
kubectl apply -f k8s/
kubectl get pods -l app=sentiment-model
```

3. Hit `/predict` in a loop to observe traffic:

```bash
kubectl port-forward service/sentiment-model 8080:8080
```

In another terminal:

```bash
while true; do
  curl -s -X POST http://localhost:8080/predict \
    -H "Content-Type: application/json" \
    -d '{"text":"great product"}'
  echo
  sleep 0.5
done
```

4. Update to v2:

```bash
kubectl set image deployment/sentiment-model app=ml-lab-04:v2
```

5. Watch the rolling update:

```bash
kubectl rollout status deployment/sentiment-model
```

6. During rollout, you may briefly see mixed v1 and v2 responses as pods rotate while maintaining availability.

7. Rollback immediately if needed:

```bash
kubectl rollout undo deployment/sentiment-model
kubectl rollout status deployment/sentiment-model
```

8. Check revision history:

```bash
kubectl rollout history deployment/sentiment-model
```

## Verification Steps

1. Confirm 3 replicas are always available:

```bash
kubectl get deployment sentiment-model
```

2. Confirm rollout strategy:

```bash
kubectl get deployment sentiment-model -o yaml
```

Verify `maxSurge: 1` and `maxUnavailable: 0`.

3. Confirm app response after update:

```bash
curl -s -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"awesome"}'
```

Expected after update:

```json
{"model_version":"v2","prediction":"positive","confidence":0.91}
```

## Cleanup

```bash
kubectl delete -f k8s/
```

## Interview Talking Points

I deploy model updates with zero downtime using rolling updates. I can rollback a bad model version in seconds with `kubectl rollout undo`.

# Lab 03: Auto-Scaling Under Load

## Scenario

Black Friday. Your product recommendation model normally handles 10 req/s. Marketing just sent a push notification to 2M users. Scale or die.

## What You'll Learn

- Horizontal Pod Autoscaler (HPA) basics
- Why CPU/memory requests and limits matter
- How metrics-server feeds autoscaling decisions
- Observe scale-out and scale-in behavior under load

## Prerequisites

- Docker Desktop Kubernetes enabled
- `kubectl` working
- Python 3.10+ for `load_test.py`

You need metrics-server installed. On Docker Desktop K8s it's usually pre-installed. If not:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## Step-by-Step Instructions

1. Build and deploy with 1 replica:

   ```bash
   docker build -t ml-lab-03:latest .
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/hpa.yaml
   kubectl get deploy ml-autoscale
   ```

2. Open service to local machine:

   ```bash
   kubectl port-forward service/ml-autoscale 8080:8080
   ```

3. Run load test in a separate terminal:

   ```bash
   python load_test.py
   ```

4. Watch HPA:

   ```bash
   kubectl get hpa -w
   ```

5. Watch pods multiply:

   ```bash
   kubectl get pods -w
   ```

6. Stop load test and observe scale-down:

   Stop the load script, then keep watching `kubectl get hpa -w` and `kubectl get pods -w` for replicas to reduce toward 1.

## Verification Steps

- `kubectl get hpa ml-autoscale` shows CPU target and changing replica count
- `kubectl get deploy ml-autoscale` shows replicas > 1 during load
- After load stops, replicas return toward minReplicas (1)

## Cleanup

```bash
kubectl delete -f k8s/
docker rmi ml-lab-03:latest
```

## Interview Talking Points

I configure horizontal pod autoscaling based on resource metrics. I understand requests vs limits and how they affect scheduling and autoscaling.

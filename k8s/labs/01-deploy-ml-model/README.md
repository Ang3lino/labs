# Lab 01: Deploy Your First ML Model

## Scenario

You trained an iris classifier in a Jupyter notebook. Your team lead says: deploy it so the frontend team can call it. You have 30 minutes.

## What You'll Learn

- Pod basics: one running container
- Deployment: desired state and replica management
- Service: stable network endpoint for pods
- Labels/selectors: how Service finds pods
- Container port mapping on Kubernetes

## Prerequisites

- Docker Desktop with Kubernetes enabled
- `kubectl` configured to your local cluster
- Docker available in terminal

```bash
kubectl get nodes
docker version
```

## Step-by-Step Instructions

1. Build the Docker image:

   ```bash
   docker build -t ml-lab-01:latest .
   ```

2. Verify locally:

   ```bash
   docker run --rm -p 8080:8080 ml-lab-01:latest
   ```

   In a second terminal:

   ```bash
   curl http://localhost:8080/health
   curl -X POST http://localhost:8080/predict -H "Content-Type: application/json" -d "{\"features\": [5.1, 3.5, 1.4, 0.2]}"
   ```

3. Apply K8s manifests:

   ```bash
   kubectl apply -f k8s/
   ```

4. Check pods:

   ```bash
   kubectl get pods
   ```

5. Test the service:

   ```bash
   kubectl get svc ml-model
   curl -X POST http://localhost:30080/predict -H "Content-Type: application/json" -d "{\"features\": [5.1, 3.5, 1.4, 0.2]}"
   ```

6. Scale:

   ```bash
   kubectl scale deployment ml-model --replicas=4
   ```

7. Observe:

   ```bash
   kubectl get pods -w
   ```

## Verification Steps

- `kubectl get deployment ml-model` shows desired/current/available replicas aligned
- `kubectl get pods -l app=ml-model` shows multiple running pods
- `/health` returns `{"status": "ok"}`
- `/predict` returns class + confidence JSON

## Cleanup

```bash
kubectl delete -f k8s/
docker rmi ml-lab-01:latest
```

## Interview Talking Points

I containerized an ML model and deployed it to Kubernetes with health checks, resource limits, and horizontal scaling.

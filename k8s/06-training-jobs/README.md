# Lab 06: Training Jobs & Scheduled Retraining

## Scenario

Your model needs weekly retraining on fresh data. Instead of a forgotten cron on one EC2 instance, you run training as a Kubernetes Job with retry logic and persistent storage for model artifacts.

## What You'll Learn

- One-shot training workloads with Jobs
- Scheduled retraining with CronJobs
- Persistent artifact storage with PVCs
- Retry behavior with `backoffLimit`
- Job lifecycle observability and debugging

## Prerequisites

- Labs 01–05 completed
- Docker Desktop with Kubernetes enabled
- `kubectl` configured to your local cluster

## Step-by-Step Instructions

1. Build the training image:

```bash
docker build -t ml-lab-06:latest .
```

2. Create PVC:

```bash
kubectl apply -f k8s/pvc.yaml
```

3. Run one-shot training:

```bash
kubectl apply -f k8s/job.yaml
```

4. Watch training status and logs:

```bash
kubectl get jobs -w
kubectl logs job/train-model
```

5. Verify model artifact in shared storage using a debug pod:

```bash
kubectl run pvc-debug --rm -it --restart=Never --image=busybox \
  --overrides='{"spec":{"volumes":[{"name":"model-storage","persistentVolumeClaim":{"claimName":"model-storage"}}],"containers":[{"name":"debug","image":"busybox","command":["sh"],"stdin":true,"tty":true,"volumeMounts":[{"name":"model-storage","mountPath":"/models"}]}]}}'
```

Inside the pod:

```sh
ls -lah /models
```

6. Deploy scheduled retraining:

```bash
kubectl apply -f k8s/cronjob.yaml
```

7. Check schedule:

```bash
kubectl get cronjobs
```

8. Manually trigger one run from CronJob:

```bash
kubectl create job --from=cronjob/weekly-retrain manual-train-1
kubectl logs job/manual-train-1
```

9. Simulate failure and retry behavior:

- Edit `train.py` to raise an exception early.
- Rebuild image and rerun `job.yaml`.
- Observe retries up to `backoffLimit: 3`.

## Verification Steps

1. Confirm Job completes:

```bash
kubectl get job train-model
```

2. Confirm model file persisted:

```bash
kubectl get pvc model-storage
```

3. Confirm CronJob exists and is scheduled:

```bash
kubectl describe cronjob weekly-retrain
```

## Cleanup

```bash
kubectl delete -f k8s/cronjob.yaml
kubectl delete -f k8s/job.yaml
kubectl delete -f k8s/pvc.yaml
kubectl delete job manual-train-1 --ignore-not-found
```

## Interview Talking Points

I orchestrate ML training as Kubernetes Jobs with retry logic and persistent artifact storage. I schedule retraining with CronJobs instead of fragile cron on EC2.

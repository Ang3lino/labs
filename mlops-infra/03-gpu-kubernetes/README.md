# Lab 03 — GPU Scheduling on Kubernetes

## Summary

Install the NVIDIA GPU Operator on K8s, schedule GPU workloads, understand time-slicing and MIG, and run ML inference jobs that request specific GPU resources. This is the bridge between "I know K8s" and "I can run ML on K8s."

## Problem It Solves

You have 4 GPU nodes in a cluster. Without GPU-aware scheduling:
- Two jobs land on the same GPU → OOM, both crash
- One job hogs a GPU 24/7 but only uses 10% of its compute
- Nobody knows which GPUs are free vs occupied
- Kubernetes has no idea GPUs exist — it only sees CPU and RAM

The NVIDIA GPU Operator makes GPUs a first-class K8s resource (`nvidia.com/gpu`) that the scheduler understands.

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────────┐
│                    K8s Control Plane                          │
│                                                              │
│  Scheduler: "Pod X requests nvidia.com/gpu: 1"               │
│             "Node A has 2 free GPUs → place it there"        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    GPU Worker Node                            │
│                                                              │
│  ┌───────────────────────────────────────────────────┐      │
│  │ NVIDIA GPU Operator (installs all of the below)   │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐     │
│  │ GPU Driver  │  │ Container    │  │ Device Plugin  │     │
│  │ (kernel     │  │ Toolkit      │  │ (advertises    │     │
│  │  module)    │  │ (nvidia-ctk) │  │  GPUs to K8s)  │     │
│  └─────────────┘  └──────────────┘  └────────────────┘     │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐     │
│  │ DCGM        │  │ MIG Manager  │  │ GPU Feature    │     │
│  │ (GPU        │  │ (partition   │  │ Discovery      │     │
│  │  metrics)   │  │  A100 into   │  │ (labels nodes) │     │
│  │             │  │  slices)     │  │                │     │
│  └─────────────┘  └──────────────┘  └────────────────┘     │
│                                                              │
│  Physical GPUs: [GPU 0: A100 80GB] [GPU 1: A100 80GB]       │
└─────────────────────────────────────────────────────────────┘
```

**The GPU Operator installs:**
1. **NVIDIA Driver** — kernel module for talking to GPU hardware
2. **Container Toolkit** — allows containers to access GPUs via `--gpus`
3. **Device Plugin** — advertises `nvidia.com/gpu: N` to K8s scheduler
4. **DCGM Exporter** — exports GPU metrics (utilization, memory, temperature) for Prometheus
5. **GPU Feature Discovery** — labels nodes with GPU model, driver version, CUDA version
6. **MIG Manager** — partitions A100/H100 into isolated GPU slices (optional)

**Scheduling flow:**
```
1. Pod spec says: resources.limits.nvidia.com/gpu: 1
2. Scheduler checks: which nodes have free nvidia.com/gpu?
3. Scheduler picks node → kubelet assigns specific GPU device
4. Container sees ONLY its assigned GPU (isolated)
5. When pod terminates → GPU returned to pool
```

**GPU sharing strategies:**

| Strategy | How | When |
|---|---|---|
| **Exclusive (default)** | 1 pod = 1 full GPU | Training, large inference |
| **Time-slicing** | Multiple pods share 1 GPU (round-robin) | Small models, development |
| **MIG (A100/H100 only)** | Hardware-partitioned into isolated slices | Multi-tenant, guaranteed isolation |
| **MPS (Multi-Process Service)** | CUDA-level sharing, no isolation | Trusted workloads, max utilization |

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **NVIDIA GPU Operator** | K8s clusters with NVIDIA GPUs. Standard. | Non-NVIDIA GPUs (AMD ROCm has its own operator) |
| **Manual driver + device plugin** | Air-gapped, need exact driver version control | Normal operations (operator is simpler) |
| **Run:ai** | Enterprise GPU scheduling with quotas, fairness, gang scheduling | Open-source-only environments |
| **Volcano** | Batch scheduling (gang scheduling, fair-share queues for training) | Simple inference serving |
| **NVIDIA NIM** | Packaged model containers (pre-optimized) | When you need control over serving stack |

**Decision rule**: If you're doing ML on K8s with NVIDIA GPUs → GPU Operator. Period. It's the standard.

## Industry Scenarios

| Company / Pattern | How GPU Scheduling Works |
|---|---|
| **HPE AI Platform** (your project) | GPU Operator on OpenShift, GPU per namespace quota, reservation system for teams |
| **OpenAI** | Thousands of GPU pods on AKS, custom scheduler for training job placement |
| **Meta** | Custom GPU scheduler (not K8s) for massive training; K8s for inference serving |
| **Any ML platform team** | GPU Operator + time-slicing for dev/test, exclusive for production inference |
| **Multi-tenant AI platform** | MIG partitioning: give Team A 3g.40gb slice, Team B 2g.20gb slice of same A100 |

## Key Terms

- `nvidia.com/gpu` — K8s extended resource
- `GPU Operator` — DaemonSet that installs all NVIDIA components
- `Device Plugin` — kubelet plugin advertising GPU count
- `DCGM (Data Center GPU Manager)` — GPU metrics collection
- `MIG (Multi-Instance GPU)` — hardware GPU partitioning (A100/H100)
- `Time-slicing` — software GPU sharing (oversubscription)
- `GPU Feature Discovery` — auto-labels nodes with GPU info
- `tolerations + nodeSelector` — target GPU nodes specifically
- `RuntimeClass` — select NVIDIA container runtime

## Interview Talking Points

"I manage GPU workloads on K8s using the NVIDIA GPU Operator. Each ML inference pod requests `nvidia.com/gpu: 1`, and the scheduler places it on nodes with available GPUs. For development clusters, I enable time-slicing so 4 data scientists can share a single GPU without blocking each other. For production inference, it's exclusive allocation — one vLLM instance per GPU for predictable latency. I use DCGM Exporter to feed GPU utilization metrics into Prometheus so we can track actual usage vs allocated and right-size our cluster."

## Exercises

### Exercise 1: Install GPU Operator on minikube

```bash
# Start minikube with GPU passthrough (requires NVIDIA GPU + driver on host)
minikube start --driver=docker --gpus=all

# Or if no local GPU, use kind with NVIDIA container runtime
# (requires nvidia-container-toolkit on host)

# Add NVIDIA Helm repo
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Install GPU Operator
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --wait

# Verify GPU is discovered
kubectl get nodes -o json | jq '.items[].status.capacity["nvidia.com/gpu"]'
```

### Exercise 2: Run a GPU pod

```yaml
# gpu-test.yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  containers:
  - name: cuda-test
    image: nvidia/cuda:12.4.1-base-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

```bash
kubectl apply -f gpu-test.yaml
kubectl logs gpu-test    # should show nvidia-smi output with GPU info
kubectl delete pod gpu-test
```

### Exercise 3: GPU resource contention

```bash
# Submit 2 pods, but you only have 1 GPU
kubectl apply -f gpu-test.yaml
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test-2
spec:
  restartPolicy: Never
  containers:
  - name: cuda-test
    image: nvidia/cuda:12.4.1-base-ubuntu22.04
    command: ["sleep", "300"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

# Observe: one runs, one Pending (insufficient nvidia.com/gpu)
kubectl get pods
kubectl describe pod gpu-test-2  # shows "Insufficient nvidia.com/gpu" in Events
```

### Exercise 4: Enable time-slicing (share GPU)

```yaml
# time-slicing-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: time-slicing-config
  namespace: gpu-operator
data:
  any: |-
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4    # 1 physical GPU → advertised as 4
```

```bash
kubectl apply -f time-slicing-config.yaml

# Patch GPU Operator to use time-slicing
kubectl patch clusterpolicies.nvidia.com/cluster-policy \
  --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"time-slicing-config","default":"any"}}}}'

# Now node advertises 4 GPUs instead of 1
kubectl get nodes -o json | jq '.items[].status.capacity["nvidia.com/gpu"]'
# Output: "4"

# All 4 pods can run (shared access, no isolation)
```

### Exercise 5: Node labeling and targeting

```bash
# See GPU labels applied by GPU Feature Discovery
kubectl get nodes --show-labels | grep nvidia

# Target specific GPU model in your pod
# nodeSelector:
#   nvidia.com/gpu.product: "NVIDIA-A10G"
```

### Exercise 6: Monitor GPU with DCGM

```bash
# DCGM exporter is already installed by GPU Operator
# Check metrics endpoint
kubectl port-forward svc/nvidia-dcgm-exporter 9400:9400 -n gpu-operator
curl localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL
# Output: DCGM_FI_DEV_GPU_UTIL{gpu="0",...} 45.0
```

## CPU-Only Fallback (No GPU Available)

If you don't have a local GPU, you can still learn the concepts:

```bash
# Use kind cluster + fake GPU resources for scheduling practice
# (won't actually run CUDA, but teaches the scheduling flow)
kubectl label node kind-worker accelerator=fake-gpu
# Then use nodeSelector in your pods to target it
```

Or use a free GPU cloud for exercises:
- Google Colab (T4 GPU)
- Lambda Cloud (free tier)
- vast.ai (cheap spot GPUs)

## References

- [NVIDIA GPU Operator docs](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/)
- [K8s device plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/)
- [Time-slicing GPUs on K8s](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/gpu-sharing.html)
- [MIG User Guide](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/)
- [Run:ai docs](https://docs.run.ai/) (enterprise alternative)

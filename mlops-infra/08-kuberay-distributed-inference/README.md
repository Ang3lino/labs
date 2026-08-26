# Lab 08 — Distributed Inference with KubeRay

## Summary

In this lab you'll deploy the KubeRay operator on your on-prem Kubernetes cluster, provision a `RayCluster` with GPU worker groups, and expose a distributed vLLM inference service using `RayService`. You'll run a 70B-parameter LLM across multiple nodes using tensor parallelism coordinated by Ray, configure the autoscaler to scale worker replicas based on request queue depth, and wire the whole stack into your Argo CD GitOps pipeline from Lab 07. By the end you'll have a production-grade distributed inference platform that can serve models too large for any single GPU node.

## Problem It Solves

Without KubeRay, distributed multi-node inference on Kubernetes is painful:

- No native K8s primitive understands a Ray cluster topology — you'd hand-craft head + worker Deployments, Services, and pod affinity rules yourself, and re-do it every model
- Tensor parallelism across nodes requires Ray's collective communication layer; without it you're limited to what fits on one node's GPU memory
- No lifecycle management: if a worker crashes mid-request, nothing reschedules it and coordinates re-joining the Ray cluster
- No autoscaling tied to actual inference queue depth — HPA scales on CPU/memory, not on pending Ray tasks or Serve request backlog
- Manual placement groups to guarantee GPU topology (same rack, same NVLink domain) are error-prone and not portable across clusters
- No `RayJob` abstraction means batch inference workloads can't cleanly acquire a cluster, run, and release resources
- Upgrading a running model without downtime requires blue/green at the Ray Serve layer — there's no CRD to express that intent declaratively

## How It Works Under the Hood

### KubeRay Operator and RayCluster Lifecycle

```
  kubectl apply -f raycluster.yaml
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                   KubeRay Operator                       │
│                                                          │
│  Watches: RayCluster, RayService, RayJob CRDs            │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Reconcile Loop                                    │  │
│  │                                                    │  │
│  │  1. Read desired spec (head + workerGroups)        │  │
│  │  2. Create head Pod  ──► mounts GCS/NFS model      │  │
│  │  3. Create worker Pods per workerGroup replicas    │  │
│  │  4. Inject RAY_ADDRESS env into all pods           │  │
│  │  5. Create ClusterIP Service for head GCS port     │  │
│  │  6. Watch pod health, requeue on failure           │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│                   RayCluster (running)                   │
│                                                          │
│  ┌─────────────────┐        ┌──────────────────────┐    │
│  │   Head Node     │        │  Worker Group: gpu    │    │
│  │                 │        │                       │    │
│  │  - GCS (Global  │◄──────►│  worker-0  (2x A100) │    │
│  │    Control      │        │  worker-1  (2x A100) │    │
│  │    Store)       │        │  worker-2  (2x A100) │    │
│  │  - Scheduler    │        └──────────────────────┘    │
│  │  - Dashboard    │                                     │
│  │  - Autoscaler   │        ┌──────────────────────┐    │
│  └─────────────────┘        │  Worker Group: cpu    │    │
│                             │                       │    │
│                             │  worker-0  (no GPU)   │    │
│                             │  worker-1  (no GPU)   │    │
│                             └──────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### RayService Architecture (Head + Workers + Ray Serve)

```
  External Traffic
        │
        ▼
┌───────────────────┐
│  Kubernetes       │
│  Service          │  ← KubeRay creates this automatically
│  (LoadBalancer /  │
│   ClusterIP)      │
└───────┬───────────┘
        │  HTTP :8000
        ▼
┌───────────────────────────────────────────────────────────┐
│  Head Node Pod                                            │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Ray Serve HTTP Proxy  (:8000)                      │ │
│  │  Routes requests to deployments via consistent hash │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │  internal Ray RPC               │
│  ┌─────────────────────▼───────────────────────────────┐ │
│  │  Serve Deployment: VLLMDeployment                   │ │
│  │  num_replicas: 1  (router replica on head)          │ │
│  └─────────────────────┬───────────────────────────────┘ │
└────────────────────────┼──────────────────────────────────┘
                         │  Ray remote calls (tensor shards)
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Worker-0    │  │ Worker-1    │  │ Worker-2    │
│             │  │             │  │             │
│ vLLM shard  │  │ vLLM shard  │  │ vLLM shard  │
│ GPU 0,1     │  │ GPU 0,1     │  │ GPU 0,1     │
│ (tp rank 0) │  │ (tp rank 1) │  │ (tp rank 2) │
└─────────────┘  └─────────────┘  └─────────────┘
  TP=3, model weights split across 6 GPUs (3 nodes x 2)
```

### Autoscaling Flow

```
┌──────────────────────────────────────────────────────────┐
│  Ray Autoscaler (runs in head pod)                       │
│                                                          │
│  Every 5s:                                               │
│    1. Query GCS for pending actor/task resource demand   │
│    2. Compare demand vs available worker capacity        │
│    3. If demand > capacity:                              │
│         ├─ Compute required worker pods                  │
│         └─ Patch RayCluster workerGroup replicas UP      │
│    4. If workers idle > idleTimeoutSeconds:              │
│         └─ Patch RayCluster workerGroup replicas DOWN    │
└─────────────────────────┬────────────────────────────────┘
                          │ patches
                          ▼
              ┌───────────────────────┐
              │  RayCluster CR        │
              │  workerGroup.replicas │
              └───────────┬───────────┘
                          │ triggers reconcile
                          ▼
              ┌───────────────────────┐
              │  KubeRay Operator     │
              │  creates/deletes      │
              │  worker Pods          │
              └───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Worker Pod           │
              │  Joins Ray cluster    │
              │  Registers GPU        │
              │  resources with GCS   │
              └───────────────────────┘
```

## Alternatives & When to Pick

| Tool | Strengths | Weaknesses | Pick When |
|---|---|---|---|
| **KubeRay** | Native multi-node Ray clusters, vLLM tensor parallelism, autoscaling tied to Ray queue depth, `RayJob` for batch | Operator overhead, Ray version coupling, head node is a SPOF without HA config | Model >40B or multi-node TP required; you already use Ray for training pipelines |
| **KServe** | Clean InferenceService CRD, Knative autoscaling, model store abstraction, good for single-node | No multi-node sharding, Knative dependency adds complexity, less mature GPU scheduling | Single-node inference, standard model formats (ONNX, TF, SKLearn), you want serverless scale-to-zero |
| **Triton Inference Server** | Highest throughput for CV/NLP models, dynamic batching, ONNX/TensorRT optimized, multi-model serving | No multi-node tensor parallelism, static model config, no distributed state | Optimized latency on one node, TensorRT models, high-throughput batch CV workloads |
| **Seldon Core** | Rich MLOps features (explainability, drift detection, A/B), good Helm support | Complex operator, inference graph overhead, slower to adopt latest LLM backends | Regulated industries needing explainability + drift + shadow deployments in one CRD |
| **vLLM standalone** | Simplest setup, best single-node LLM throughput, PagedAttention, continuous batching | No K8s lifecycle management, no autoscaling, one Deployment per model, no multi-node | Prototyping, single A100 node, you want zero operator overhead and manage scaling yourself |

## Industry Scenarios

| Company / Pattern | How They Use Ray / KubeRay |
|---|---|
| Anyscale | Originated Ray; uses KubeRay for their managed cloud platform to provision per-user Ray clusters on demand |
| Shopify | Runs distributed model training and batch inference pipelines on Ray on Kubernetes for recommendation models |
| Instacart | Uses Ray Serve for real-time ML model serving with autoscaling across multiple GPU node pools |
| LinkedIn | Ray for distributed feature computation and batch inference at scale; KubeRay manages cluster lifecycle on internal K8s |
| HPE Machine Learning Development Environment | Integrates Ray on top of K8s for distributed training; KubeRay is the recommended path for on-prem Ray cluster management |
| OpenAI (internal tooling) | Ray underpins large-scale distributed training infrastructure; Ray Serve used for internal inference microservices |
| General: multi-tenant LLM platform | One KubeRay operator per cluster, one `RayService` per model tier (7B, 70B, 405B), namespaced isolation, GitOps-managed via Argo CD |

## Key Terms

- **RayCluster**: A CRD that describes a Ray cluster topology — one head node spec and one or more `workerGroups`. KubeRay reconciles it into Pods and Services.
- **RayService**: A CRD that wraps a `RayCluster` plus a Ray Serve application config. Handles zero-downtime upgrades by standing up a new cluster before tearing down the old one.
- **RayJob**: A CRD for a one-shot Ray workload. KubeRay provisions a cluster, runs the job, and optionally tears the cluster down on completion. Used for batch inference.
- **Head node**: The single Ray cluster coordinator pod. Runs the Global Control Store (GCS), the scheduler, the Ray Dashboard, and the autoscaler. Not a data-plane bottleneck but a SPOF unless HA GCS is enabled.
- **Worker group**: A set of Ray worker pods with identical resource specs (GPU type, CPU, memory). A `RayCluster` can have multiple worker groups with different specs — e.g., one GPU group for inference actors, one CPU group for preprocessing.
- **Ray Serve**: Ray's model serving layer. Defines `Deployments` (stateless replicas) and `Ingress` routing. Supports batching, streaming, and pipeline DAGs. The vLLM `AsyncLLMEngine` runs inside a Serve Deployment.
- **Actor**: A stateful Ray object that holds GPU memory and handles requests. Each vLLM tensor-parallel worker shard is an actor. Actors are placed on specific nodes by the Ray scheduler.
- **Placement group**: A Ray primitive that reserves a bundle of resources (CPUs, GPUs) on specific nodes in a single atomic request. Used by vLLM to ensure all TP shards land on nodes that can communicate over NVLink or InfiniBand.
- **Autoscaler**: The Ray component (running in the head pod) that monitors resource demand in GCS and patches the `RayCluster` CR to scale worker groups up or down. It's Ray-aware, not HPA — it scales on pending actor/task demand, not CPU%.

## Interview Talking Points

"On the HPE platform we had a Llama-3 70B model that didn't fit on a single A100 80GB node — we needed tensor parallelism across three nodes, six GPUs total. KServe got us to the door but couldn't cross it; it has no multi-node sharding story. We deployed the KubeRay operator via Helm, defined a `RayCluster` with a single head and a GPU worker group of three replicas, and used a `RayService` pointing at a vLLM `AsyncLLMEngine` configured with `tensor_parallel_size=6`. KubeRay handled the entire cluster lifecycle: injecting `RAY_ADDRESS`, creating the head Service, and restarting workers that fell off. The Ray autoscaler let us idle the worker group down to one replica overnight and back up to three during peak batch reranking jobs, which cut our GPU reservation cost by about 60% outside business hours. We also wired the `RayService` manifest into the same Argo CD app as the rest of the inference stack so model upgrades went through the same PR review and sync process as everything else — no snowflake `kubectl apply` on the prod cluster."

## Exercises

### Exercise 1: Install KubeRay Operator via Helm

Add the KubeRay Helm repo and install the operator into its own namespace.

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace \
  --version 1.1.1 \
  --set image.tag=v1.1.1

# Verify the operator is running
kubectl -n kuberay-system get pods
kubectl -n kuberay-system get crd | grep ray
```

Expected CRDs after install:

```
rayclusters.ray.io
rayjobs.ray.io
rayservices.ray.io
```

---

### Exercise 2: Deploy a RayCluster (Head + 2 Workers)

Create a `RayCluster` with one head node and two GPU workers. Save as `raycluster-base.yaml`.

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: hpe-inference-cluster
  namespace: inference
spec:
  rayVersion: "2.10.0"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
      num-cpus: "0"          # head node handles no actor work
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray-ml:2.10.0-gpu
            resources:
              requests:
                cpu: "4"
                memory: "16Gi"
              limits:
                cpu: "4"
                memory: "16Gi"
            env:
              - name: RAY_DISABLE_DOCKER_CPU_WARNING
                value: "1"
        tolerations:
          - key: "node-role"
            operator: "Equal"
            value: "ray-head"
            effect: "NoSchedule"
  workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 2
      minReplicas: 1
      maxReplicas: 4
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray-ml:2.10.0-gpu
              resources:
                requests:
                  cpu: "8"
                  memory: "48Gi"
                  nvidia.com/gpu: "2"
                limits:
                  cpu: "8"
                  memory: "48Gi"
                  nvidia.com/gpu: "2"
          nodeSelector:
            node.kubernetes.io/gpu: "a100"
          tolerations:
            - key: "nvidia.com/gpu"
              operator: "Exists"
              effect: "NoSchedule"
```

```bash
kubectl create namespace inference
kubectl apply -f raycluster-base.yaml

# Wait for cluster to be ready
kubectl -n inference get raycluster hpe-inference-cluster
kubectl -n inference get pods -l ray.io/cluster=hpe-inference-cluster

# Port-forward the Ray Dashboard
kubectl -n inference port-forward svc/hpe-inference-cluster-head-svc 8265:8265
# Open http://localhost:8265
```

---

### Exercise 3: Deploy a RayService with a Simple Serve App

Package a minimal Ray Serve application and expose it via `RayService`. This confirms the operator can manage the Serve lifecycle before adding vLLM weight.

Create `serve-app.py` (baked into a ConfigMap or container image in production; inline here for clarity):

```python
# serve_app.py — drop this into your container image at /app/serve_app.py
import ray
from ray import serve
from starlette.requests import Request

@serve.deployment(num_replicas=2, ray_actor_options={"num_cpus": 1})
class EchoDeployment:
    async def __call__(self, request: Request) -> dict:
        body = await request.json()
        return {"echo": body, "node": ray.get_runtime_context().get_node_id()}

app = EchoDeployment.bind()
```

```yaml
# rayservice-echo.yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: echo-service
  namespace: inference
spec:
  serviceUnhealthySecondThreshold: 300
  deploymentUnhealthySecondThreshold: 300
  serveConfigV2: |
    applications:
      - name: echo
        import_path: serve_app:app
        runtime_env:
          working_dir: "https://your-artifact-store/serve_app.tar.gz"
        deployments:
          - name: EchoDeployment
            num_replicas: 2
            ray_actor_options:
              num_cpus: 1
  rayClusterConfig:
    rayVersion: "2.10.0"
    headGroupSpec:
      rayStartParams:
        dashboard-host: "0.0.0.0"
        num-cpus: "0"
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray-ml:2.10.0
              resources:
                requests:
                  cpu: "2"
                  memory: "8Gi"
                limits:
                  cpu: "2"
                  memory: "8Gi"
    workerGroupSpecs:
      - groupName: serve-workers
        replicas: 2
        rayStartParams: {}
        template:
          spec:
            containers:
              - name: ray-worker
                image: rayproject/ray-ml:2.10.0
                resources:
                  requests:
                    cpu: "2"
                    memory: "8Gi"
                  limits:
                    cpu: "2"
                    memory: "8Gi"
```

```bash
kubectl apply -f rayservice-echo.yaml

# Watch RayService status — it goes: WaitForServeDeploymentReady → Running
kubectl -n inference get rayservice echo-service -w

# Once Running, hit the Serve endpoint
kubectl -n inference port-forward svc/echo-service-serve-svc 8000:8000
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"message": "hello from lab 08"}'
```

---

### Exercise 4: Run vLLM on Ray with Tensor Parallelism

Deploy Llama-3-70B across 3 GPU workers using vLLM's tensor parallel backend. Each worker gets 2x A100 80GB, giving 6 GPUs total and enough VRAM for fp16 weights.

The vLLM Serve deployment handles routing; Ray manages the distributed actor placement.

```yaml
# rayservice-vllm-70b.yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: llama3-70b
  namespace: inference
spec:
  serviceUnhealthySecondThreshold: 600
  deploymentUnhealthySecondThreshold: 600
  serveConfigV2: |
    applications:
      - name: llama3-70b
        import_path: vllm.entrypoints.openai.api_server:build_app
        args:
          model: /mnt/models/llama3-70b-instruct
          tensor-parallel-size: "6"
          pipeline-parallel-size: "1"
          gpu-memory-utilization: "0.90"
          max-model-len: "8192"
          served-model-name: llama3-70b-instruct
          trust-remote-code: "false"
        deployments:
          - name: VLLMDeployment
            num_replicas: 1
            ray_actor_options:
              num_gpus: 6
        runtime_env:
          pip:
            - vllm==0.4.2
          env_vars:
            VLLM_WORKER_MULTIPROC_METHOD: spawn
            NCCL_DEBUG: WARN
  rayClusterConfig:
    rayVersion: "2.10.0"
    headGroupSpec:
      rayStartParams:
        dashboard-host: "0.0.0.0"
        num-cpus: "0"
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray-ml:2.10.0-gpu
              resources:
                requests:
                  cpu: "4"
                  memory: "16Gi"
                limits:
                  cpu: "4"
                  memory: "16Gi"
          volumes:
            - name: model-store
              nfs:
                server: nfs.hpe-mlops.local
                path: /models
    workerGroupSpecs:
      - groupName: gpu-workers-a100
        replicas: 3
        minReplicas: 3
        maxReplicas: 3       # fixed for TP=6; scaling changes the TP topology
        rayStartParams: {}
        template:
          spec:
            containers:
              - name: ray-worker
                image: rayproject/ray-ml:2.10.0-gpu
                resources:
                  requests:
                    cpu: "16"
                    memory: "120Gi"
                    nvidia.com/gpu: "2"
                  limits:
                    cpu: "16"
                    memory: "120Gi"
                    nvidia.com/gpu: "2"
                volumeMounts:
                  - name: model-store
                    mountPath: /mnt/models
            volumes:
              - name: model-store
                nfs:
                  server: nfs.hpe-mlops.local
                  path: /models
            nodeSelector:
              node.kubernetes.io/gpu: "a100-80gb"
            tolerations:
              - key: "nvidia.com/gpu"
                operator: "Exists"
                effect: "NoSchedule"
```

```bash
kubectl apply -f rayservice-vllm-70b.yaml

# Monitor pod scheduling — all 3 workers must land before vLLM initializes
kubectl -n inference get pods -l ray.io/cluster=llama3-70b -w

# Watch RayService converge (takes ~3-5 min for model load across 6 GPUs)
kubectl -n inference get rayservice llama3-70b -w

# Test the OpenAI-compatible endpoint
kubectl -n inference port-forward svc/llama3-70b-serve-svc 8000:8000
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3-70b-instruct",
    "messages": [{"role": "user", "content": "Explain tensor parallelism in two sentences."}],
    "max_tokens": 200
  }'
```

---

### Exercise 5: Configure Autoscaling (min/max Workers, idleTimeout)

Enable Ray autoscaling so the 7B worker group scales with request volume. The 70B cluster from Exercise 4 uses fixed replicas because the TP topology is rigid — autoscaling applies cleanly to smaller models with `num_replicas > 1` in Serve.

```yaml
# rayservice-vllm-7b-autoscale.yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: llama3-7b
  namespace: inference
spec:
  serviceUnhealthySecondThreshold: 300
  deploymentUnhealthySecondThreshold: 300
  serveConfigV2: |
    applications:
      - name: llama3-7b
        import_path: vllm.entrypoints.openai.api_server:build_app
        args:
          model: /mnt/models/llama3-7b-instruct
          tensor-parallel-size: "1"
          gpu-memory-utilization: "0.85"
          max-model-len: "8192"
          served-model-name: llama3-7b-instruct
        deployments:
          - name: VLLMDeployment
            num_replicas: 2
            autoscaling_config:
              min_replicas: 1
              max_replicas: 6
              target_num_ongoing_requests_per_replica: 10
              upscale_delay_s: 30
              downscale_delay_s: 300
            ray_actor_options:
              num_gpus: 1
        runtime_env:
          pip:
            - vllm==0.4.2
  rayClusterConfig:
    rayVersion: "2.10.0"
    enableInTreeAutoscaling: true
    autoscalerOptions:
      upscalingMode: Default
      idleTimeoutSeconds: 600
      resources:
        requests:
          cpu: "500m"
          memory: "512Mi"
        limits:
          cpu: "1"
          memory: "1Gi"
    headGroupSpec:
      rayStartParams:
        dashboard-host: "0.0.0.0"
        num-cpus: "0"
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray-ml:2.10.0-gpu
              resources:
                requests:
                  cpu: "4"
                  memory: "16Gi"
                limits:
                  cpu: "4"
                  memory: "16Gi"
    workerGroupSpecs:
      - groupName: gpu-workers-7b
        replicas: 2
        minReplicas: 1
        maxReplicas: 6
        rayStartParams: {}
        template:
          spec:
            containers:
              - name: ray-worker
                image: rayproject/ray-ml:2.10.0-gpu
                resources:
                  requests:
                    cpu: "8"
                    memory: "32Gi"
                    nvidia.com/gpu: "1"
                  limits:
                    cpu: "8"
                    memory: "32Gi"
                    nvidia.com/gpu: "1"
                volumeMounts:
                  - name: model-store
                    mountPath: /mnt/models
            volumes:
              - name: model-store
                nfs:
                  server: nfs.hpe-mlops.local
                  path: /models
            nodeSelector:
              node.kubernetes.io/gpu: "a100-80gb"
            tolerations:
              - key: "nvidia.com/gpu"
                operator: "Exists"
                effect: "NoSchedule"
```

```bash
kubectl apply -f rayservice-vllm-7b-autoscale.yaml

# Watch autoscaler decisions in the head pod logs
HEAD_POD=$(kubectl -n inference get pods \
  -l ray.io/cluster=llama3-7b,ray.io/node-type=head \
  -o jsonpath='{.items[0].metadata.name}')

kubectl -n inference logs $HEAD_POD -c autoscaler -f

# Generate load to trigger scale-up
kubectl -n inference port-forward svc/llama3-7b-serve-svc 8000:8000 &
for i in $(seq 1 50); do
  curl -s -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"llama3-7b-instruct","messages":[{"role":"user","content":"Count to 100."}],"max_tokens":300}' &
done
wait

# Watch worker count change
kubectl -n inference get pods -l ray.io/cluster=llama3-7b -w
```

---

### Exercise 6: Deploy via Argo CD (GitOps Integration — Lab 07 Continuation)

Commit the `RayService` manifests to your GitOps repo and have Argo CD manage the lifecycle. This connects to the Argo CD `AppProject` and `Application` you set up in Lab 07.

Directory layout in your GitOps repo:

```
gitops-repo/
└── clusters/
    └── hpe-on-prem/
        └── inference/
            ├── kustomization.yaml
            ├── namespace.yaml
            ├── rayservice-vllm-7b-autoscale.yaml
            └── rayservice-vllm-70b.yaml
```

```yaml
# gitops-repo/clusters/hpe-on-prem/inference/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - rayservice-vllm-7b-autoscale.yaml
  - rayservice-vllm-70b.yaml
```

```yaml
# argocd-app-inference.yaml — apply to your Argo CD namespace (lab 07 cluster)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: inference-rayservices
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: mlops-infra          # AppProject from Lab 07
  source:
    repoURL: https://github.com/your-org/gitops-repo
    targetRevision: main
    path: clusters/hpe-on-prem/inference
  destination:
    server: https://kubernetes.default.svc
    namespace: inference
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true   # required for large CRD manifests
    retry:
      limit: 5
      backoff:
        duration: 10s
        factor: 2
        maxDuration: 3m
```

```bash
# Commit manifests and push
git -C gitops-repo add clusters/hpe-on-prem/inference/
git -C gitops-repo commit -m "feat(inference): add KubeRay RayService deployments for 7B and 70B"
git -C gitops-repo push origin main

# Register the Argo CD Application
kubectl apply -f argocd-app-inference.yaml

# Watch sync
argocd app get inference-rayservices
argocd app sync inference-rayservices --watch

# Verify resources are healthy
argocd app wait inference-rayservices --health --timeout 600
kubectl -n inference get rayservice -w
```

To roll out a new vLLM version, update the `image` tag or `pip` version in the manifest, open a PR, and merge. Argo CD detects the diff and syncs. KubeRay's `RayService` upgrade logic provisions a new cluster in parallel, waits for Serve to be healthy, then cuts traffic over and tears down the old cluster — zero downtime.

## References

- [KubeRay Documentation](https://docs.ray.io/en/latest/cluster/kubernetes/index.html)
- [KubeRay GitHub](https://github.com/ray-project/kuberay)
- [KubeRay Helm Chart](https://github.com/ray-project/kuberay-helm)
- [RayCluster CRD Reference](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/raycluster-quick-start.html)
- [RayService CRD Reference](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/rayservice-quick-start.html)
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/index.html)
- [vLLM Distributed Inference with Ray](https://docs.vllm.ai/en/latest/serving/distributed_serving.html)
- [vLLM on KubeRay Example](https://docs.ray.io/en/latest/cluster/kubernetes/examples/vllm-rayservice.html)
- [Ray Autoscaler on Kubernetes](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/configuring-autoscaling.html)
- [Argo CD Application CRD](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)

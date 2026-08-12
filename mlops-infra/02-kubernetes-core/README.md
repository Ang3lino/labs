# Lab 02 — Kubernetes Core

## Summary

Deploy, scale, and expose a containerized ML service on Kubernetes. By the end you'll understand Pods, Deployments, Services, ConfigMaps, Secrets, Namespaces, RBAC, PVCs, and Ingress — the building blocks everything else runs on.

## Problem It Solves

You have 50 containers across 10 machines. Without an orchestrator:
- Who decides which machine runs which container?
- Container crashes at 3am → who restarts it?
- New version → how do you update without downtime?
- Team A needs 4 GPUs, Team B needs 2 → who enforces this?
- Container needs to talk to another container → how does it find it?

Kubernetes answers all of these. It's the operating system for your cluster.

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────────────┐
│                      Control Plane                                │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ API      │  │ Scheduler    │  │ Controller │  │ etcd     │  │
│  │ Server   │  │              │  │ Manager    │  │ (state)  │  │
│  │          │  │ "Where does  │  │ "Are N     │  │          │  │
│  │ kubectl  │  │  this pod    │  │  replicas  │  │ All      │  │
│  │ talks to │  │  fit best?"  │  │  running?" │  │ cluster  │  │
│  │ this     │  │              │  │            │  │ state    │  │
│  └──────────┘  └──────────────┘  └────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Worker Node   │  │   Worker Node   │  │   Worker Node   │
│                 │  │                 │  │                 │
│  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │
│  │  kubelet  │  │  │  │  kubelet  │  │  │  │  kubelet  │  │
│  │  (agent)  │  │  │  │  (agent)  │  │  │  │  (agent)  │  │
│  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │
│                 │  │                 │  │                 │
│  ┌────┐ ┌────┐ │  │  ┌────┐ ┌────┐ │  │  ┌────┐        │
│  │Pod │ │Pod │ │  │  │Pod │ │Pod │ │  │  │Pod │        │
│  │ A  │ │ B  │ │  │  │ C  │ │ D  │ │  │  │ E  │        │
│  └────┘ └────┘ │  │  └────┘ └────┘ │  │  └────┘        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

**The reconciliation loop (core concept):**
```
You declare: "I want 3 replicas of my-model"
                    ↓
Controller checks: "Currently 2 running"
                    ↓
Controller acts:   "Start 1 more pod"
                    ↓
Scheduler decides: "Node 2 has capacity → place it there"
                    ↓
Kubelet on Node 2: pulls image, starts container
                    ↓
Repeat forever (every few seconds)
```

This is **declarative** — you state desired state, K8s converges to it. You never say "start a container on machine X". You say "I want 3 running" and K8s figures out where/how.

**Key objects and their relationships:**

| Object | What it is | Analogy |
|---|---|---|
| **Pod** | Smallest unit. 1+ containers sharing network/storage. | A running process |
| **Deployment** | Manages N pod replicas. Handles rolling updates. | A service manager |
| **Service** | Stable network endpoint pointing to a set of pods. | A DNS name + load balancer |
| **ConfigMap** | Key-value config injected into pods. | Environment variables file |
| **Secret** | Like ConfigMap but base64-encoded (not encrypted at rest by default). | Credentials store |
| **Namespace** | Virtual cluster within a cluster. Isolation boundary. | A folder/tenant |
| **PersistentVolumeClaim** | Request for storage. Bound to actual disk. | "Give me 100GB" |
| **Ingress** | HTTP routing from outside to Services inside. | Reverse proxy rules |
| **RBAC (Role/RoleBinding)** | Who can do what. | IAM policies |

**Networking model:**
- Every pod gets its own IP (no port conflicts)
- Pods can talk to any pod on any node (flat network)
- Services provide stable DNS: `my-svc.my-namespace.svc.cluster.local`
- Ingress exposes HTTP routes externally

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **Kubernetes** | Multi-service, multi-team, need scaling/self-healing/GPU scheduling | Single container, personal project, <5 containers |
| **Docker Compose** | Local dev, single machine, <10 containers | Production, multi-node, need auto-scaling |
| **ECS Fargate** | AWS-only, simpler than K8s, no node management | Multi-cloud, need K8s ecosystem tools |
| **Nomad (HashiCorp)** | Simpler than K8s, multi-workload (containers + VMs + batch) | When team already knows K8s or needs K8s ecosystem |
| **Bare Docker + systemd** | 1-2 containers on a VM, simplest possible | Anything beyond trivial |

**Decision rule**: If you need auto-scaling, self-healing, rolling deploys, GPU scheduling, or multi-tenancy → K8s. Otherwise, Docker Compose is fine.

## Industry Scenarios

| Company | How K8s Is Used |
|---|---|
| **HPE AI Platform** (your project) | Platform substrate. Every inference runtime, API gateway, observability stack runs on K8s/OpenShift with GPU operators |
| **Spotify** | 2000+ microservices on GKE. ML models served alongside backend services |
| **Uber** | Peloton → K8s migration. All ML training and serving on K8s |
| **OpenAI** | Training clusters orchestrated on K8s (Azure AKS). Thousands of GPU pods |
| **Any bank/enterprise** | Multi-tenant platform: each team gets a namespace with resource quotas |

## Key Terms

- `Pod` — smallest deployable unit
- `Deployment` — manages replica sets and rolling updates
- `Service` (ClusterIP, NodePort, LoadBalancer) — stable networking
- `Namespace` — isolation boundary
- `ConfigMap` / `Secret` — config injection
- `PersistentVolumeClaim (PVC)` — storage request
- `Ingress` / `IngressController` — HTTP routing
- `RBAC` (Role, ClusterRole, RoleBinding) — access control
- `Resource requests/limits` — CPU/memory guarantees and caps
- `kubectl` — CLI client
- `Helm` — package manager for K8s (charts = templates)
- `kustomize` — overlay-based config management
- `HPA (Horizontal Pod Autoscaler)` — scale pods based on metrics

## Interview Talking Points

"I deploy ML services on Kubernetes using Deployments with resource requests and limits to guarantee GPU and memory allocation. Services expose model endpoints internally; Ingress handles external routing with TLS. I use Namespaces for team isolation with RBAC and ResourceQuotas. Rolling updates give zero-downtime deploys — I've used canary patterns with traffic splitting for model A/B tests. For storage, PVCs backed by NFS hold model weights shared across replicas."

## Exercises

### Exercise 1: Set up local cluster

```bash
# Install minikube (or use kind)
minikube start --cpus=4 --memory=8192 --driver=docker

# Verify
kubectl cluster-info
kubectl get nodes
```

### Exercise 2: Deploy an ML inference service

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sentiment-api
  namespace: ml-serving
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sentiment-api
  template:
    metadata:
      labels:
        app: sentiment-api
    spec:
      containers:
      - name: inference
        image: youruser/ml-inference:v1  # from Lab 01
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1000m"
            memory: "2Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: sentiment-api
  namespace: ml-serving
spec:
  selector:
    app: sentiment-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

```bash
kubectl create namespace ml-serving
kubectl apply -f deployment.yaml
kubectl get pods -n ml-serving -w          # watch pods come up
kubectl port-forward svc/sentiment-api 8000:80 -n ml-serving
curl localhost:8000/health                  # test it
```

### Exercise 3: ConfigMaps and Secrets

```yaml
# config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-config
  namespace: ml-serving
data:
  MODEL_NAME: "distilbert-base-uncased"
  MAX_BATCH_SIZE: "32"
  LOG_LEVEL: "info"
---
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
  namespace: ml-serving
type: Opaque
stringData:
  HF_TOKEN: "hf_your_token_here"
```

Inject into the Deployment:
```yaml
envFrom:
- configMapRef:
    name: model-config
- secretRef:
    name: api-keys
```

### Exercise 4: Scaling and self-healing

```bash
# Scale manually
kubectl scale deployment sentiment-api --replicas=5 -n ml-serving

# Watch pods distribute across nodes
kubectl get pods -o wide -n ml-serving

# Kill a pod — observe K8s restart it
kubectl delete pod <pod-name> -n ml-serving
kubectl get pods -n ml-serving -w

# HPA (auto-scale on CPU)
kubectl autoscale deployment sentiment-api \
  --cpu-percent=70 --min=2 --max=10 -n ml-serving
```

### Exercise 5: RBAC and Namespaces (multi-tenant)

```yaml
# team-a-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "8"
    requests.memory: "32Gi"
    limits.cpu: "16"
    limits.memory: "64Gi"
    pods: "20"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: team-a-dev
  namespace: team-a
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "deployments", "services"]
  verbs: ["get", "list", "create", "update", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: team-a-dev-binding
  namespace: team-a
subjects:
- kind: User
  name: alice
roleRef:
  kind: Role
  name: team-a-dev
  apiGroup: rbac.authorization.k8s.io
```

```bash
kubectl apply -f team-a-namespace.yaml
# Alice can deploy in team-a, but not in team-b
```

### Exercise 6: Persistent storage

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-weights
  namespace: ml-serving
spec:
  accessModes: [ReadOnlyMany]
  resources:
    requests:
      storage: 10Gi
```

Mount in your Deployment:
```yaml
volumeMounts:
- name: weights
  mountPath: /models
  readOnly: true
volumes:
- name: weights
  persistentVolumeClaim:
    claimName: model-weights
```

### Exercise 7: Rolling update (zero downtime)

```bash
# Update image version
kubectl set image deployment/sentiment-api \
  inference=youruser/ml-inference:v2 -n ml-serving

# Watch the rollout
kubectl rollout status deployment/sentiment-api -n ml-serving

# Something wrong? Rollback
kubectl rollout undo deployment/sentiment-api -n ml-serving
```

## References

- [Kubernetes official tutorials](https://kubernetes.io/docs/tutorials/)
- [CKAD curriculum](https://github.com/cncf/curriculum)
- *Kubernetes Up & Running* (Hightower, Burns, Beda)
- [Katacoda K8s playground](https://killercoda.com/kubernetes)
- *Designing Machine Learning Systems* Ch.7 (Deployment)

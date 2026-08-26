# Lab 07 — GitOps with Argo CD

## Summary

In this lab you'll install Argo CD on a local Kubernetes cluster and use it to declaratively manage the full lifecycle of an HPE AI inference platform stack. You'll deploy a KubeRay operator and a vLLM-backed RayServe application entirely through Git commits, wire up sync waves so dependencies come up in the right order, build an ApplicationSet that fans a single app definition out to staging and prod namespaces, and lock down multi-team access with AppProjects and RBAC. By the end, every change to your inference platform — model updates, resource quota bumps, new serving endpoints — flows through a pull request, and Argo CD enforces that the cluster always converges to what Git says.

---

## Problem It Solves

Without a GitOps controller like Argo CD, operating an ML serving platform at scale produces a predictable set of failures:

- **No audit trail.** `kubectl apply` from a laptop leaves no record of who changed what, when, or why. Post-incident investigation becomes a blame game.
- **Config drift.** Someone patches a Deployment in prod to unblock a hotfix and never commits it. The cluster and the repo diverge silently. The next deploy overwrites the fix, or never gets written at all.
- **Fragile deploy pipelines.** CI pipelines that `kubectl apply` over SSH need cluster credentials baked into the CI runner. One secret rotation breaks every pipeline.
- **No self-healing.** A human or rogue controller deletes a resource. Nothing notices. Inference goes dark until the next scheduled deploy.
- **Multi-env complexity.** Keeping staging and prod in sync without copy-pasting manifests everywhere requires scripting that grows into its own maintenance burden.
- **Rollback is manual.** Rolling back means finding the last known-good commit, re-running the pipeline, and hoping the pipeline itself hasn't changed. With large model serving stacks, this takes time the on-call engineer doesn't have.

---

## How It Works Under the Hood

### The GitOps Reconciliation Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitOps Reconciliation Loop                    │
│                                                                       │
│   Developer                  Git Repo               Argo CD           │
│   ─────────                  ────────               ───────           │
│                                                                       │
│   git push ──────────────► main branch                               │
│                              │                                        │
│                              │   (poll every 3m or webhook)           │
│                              ▼                                        │
│                         ┌────────┐    desired state                   │
│                         │  Git   │ ─────────────────►  ┌──────────┐  │
│                         │  repo  │                     │  Argo CD  │  │
│                         └────────┘                     │  server  │  │
│                                                         └────┬─────┘  │
│                                                              │         │
│                                            compare           │         │
│   ┌─────────────────────────────────────────────────────────┘         │
│   │                                                                    │
│   │   cluster live state                                               │
│   ▼                                                                    │
│  ┌────────────────┐    diff found?                                     │
│  │  Kubernetes    │ ◄──────────────  sync (kubectl apply equivalent)  │
│  │  API server    │                                                    │
│  └────────────────┘                                                    │
│          │                                                             │
│          │  actual state reported back                                 │
│          └────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
```

Argo CD polls Git (or receives a webhook) and computes a diff between desired state (Git) and live state (cluster). If they differ, it syncs. If `selfHeal: true`, it also watches for out-of-band changes on the cluster and converges back to Git automatically.

### Application CRD Lifecycle

```
┌───────────────────────────────────────────────────────────────────┐
│                   Application CRD State Machine                    │
│                                                                    │
│   kubectl apply  ──►  Application CR created                      │
│                              │                                     │
│                              ▼                                     │
│                    ┌──────────────────┐                            │
│                    │    Unknown        │  (initial, before first   │
│                    │  (health/sync)    │   refresh)                │
│                    └────────┬─────────┘                            │
│                             │  refresh                             │
│                             ▼                                      │
│                  ┌─────────────────────┐                           │
│                  │  OutOfSync / Healthy │  Git differs from        │
│                  │  or Missing          │  cluster                 │
│                  └──────────┬──────────┘                           │
│                             │  sync triggered (manual or auto)    │
│                             ▼                                      │
│                    ┌─────────────────┐                             │
│                    │   Syncing        │  resources being applied   │
│                    └──────┬──────────┘                             │
│                           │                                        │
│              ┌────────────┴────────────┐                          │
│              ▼                         ▼                           │
│   ┌─────────────────┐      ┌────────────────────┐                 │
│   │  Synced /        │      │  Synced /           │                │
│   │  Healthy         │      │  Degraded           │                │
│   │  (happy path)    │      │  (pods crashing,    │                │
│   └─────────────────┘      │   hooks failed)     │                │
│                             └────────────────────┘                │
└───────────────────────────────────────────────────────────────────┘
```

### Sync Waves — Ordered Rollout

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Sync Wave Execution Order                      │
│                                                                        │
│  Wave -1  ┌──────────────────────────────────────────────┐           │
│           │  Namespace, ResourceQuota, LimitRange         │           │
│           └──────────────────────┬───────────────────────┘           │
│                                  │  all healthy before next wave      │
│  Wave 0   ┌──────────────────────▼───────────────────────┐           │
│           │  KubeRay Operator CRDs + Operator Deployment  │           │
│           └──────────────────────┬───────────────────────┘           │
│                                  │                                    │
│  Wave 1   ┌──────────────────────▼───────────────────────┐           │
│           │  RayCluster CR  +  PVC (model weights store)  │           │
│           └──────────────────────┬───────────────────────┘           │
│                                  │                                    │
│  Wave 2   ┌──────────────────────▼───────────────────────┐           │
│           │  RayService CR  (vLLM serving endpoint)       │           │
│           └──────────────────────┬───────────────────────┘           │
│                                  │                                    │
│  Wave 3   ┌──────────────────────▼───────────────────────┐           │
│           │  Ingress + HPA + PrometheusRule                │           │
│           └──────────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────────────────┘
```

Sync waves are set via the annotation `argocd.argoproj.io/sync-wave: "0"` on each manifest. Argo CD will not advance to the next wave until all resources in the current wave reach a Healthy status.

---

## Alternatives & When to Pick

| Tool | Model | Strengths | Weaknesses | Pick it when... |
|------|-------|-----------|------------|-----------------|
| **Argo CD** | Pull (agent in cluster) | Rich UI, Application CRD, sync waves, app-of-apps, AppProject RBAC | More complex install than Flux, opinionated CRD model | You need a UI, multi-team isolation, or fine-grained sync ordering |
| **FluxCD** | Pull (agent in cluster) | Lightweight, CNCF graduated, native Helm/Kustomize, image automation | No built-in UI, less mature RBAC story | Simpler clusters, GitOps purists, image tag automation is a priority |
| **Jenkins** | Push (CI server calls kubectl) | Familiar to most orgs, massive plugin ecosystem | Credentials in CI, no self-healing, stateful server to maintain | You already run Jenkins and GitOps adoption is incremental |
| **Spinnaker** | Push (orchestration server) | Multi-cloud pipelines, canary + blue/green native, approval gates | Heavy infrastructure footprint, steep learning curve | Enterprise multi-cloud with complex promotion workflows |
| **Tekton** | Push (in-cluster pipelines) | Kubernetes-native CI/CD primitives, composable tasks | No GitOps sync loop, no self-healing, verbose YAML | You need in-cluster build pipelines; pair with Argo CD for delivery |

For the HPE AI inference platform: Argo CD + Tekton is a natural pairing. Tekton builds and pushes the model server image; Argo CD detects the new image tag in Git and rolls it out to the cluster.

---

## Industry Scenarios

| Company / Pattern | How They Use Argo CD |
|-------------------|----------------------|
| **Intuit** | App-of-apps pattern managing 50+ microservices across prod/staging. AppProjects enforce team blast-radius boundaries. |
| **Red Hat OpenShift GitOps** | Argo CD is the default GitOps engine in OpenShift. Operators and cluster config are reconciled from Git at install time. |
| **Shopify** | Argo CD drives model and feature store deployments. Sync waves sequence database migrations before application rollout. |
| **HPE / Determined AI** | Model checkpoints and serving configs tracked in Git. Argo CD + ApplicationSets fan deployments across GPU node pools in different data centers. |
| **Datadog** | Internal ML platform uses Argo CD to promote model serving configs from shadow to canary to production, gated by automated evaluation metrics. |
| **CERN** | Physics workload management on bare-metal K8s. Argo CD manages GPU operator, storage CSI, and inference service configs from a monorepo. |

---

## Key Terms

- **Application (CRD):** The core Argo CD custom resource. It maps a Git source (repo + path + revision) to a cluster destination (cluster + namespace) and declares sync policy.
- **AppProject:** A namespace-scoped resource that restricts which repos, clusters, and namespaces an Application can target. Used for team isolation and RBAC.
- **ApplicationSet:** A controller that generates multiple Application CRs from a single template, using generators (list, git directory, cluster, matrix) to fan out across environments or clusters.
- **Sync Wave:** An ordering primitive. Resources annotated with lower wave numbers are applied and must become Healthy before resources in higher waves are touched.
- **Sync Hook:** A Job or workflow triggered at specific points in the sync lifecycle: PreSync, Sync, PostSync, SyncFail. Used for migrations, smoke tests, notifications.
- **Self-heal:** When `selfHeal: true`, Argo CD watches the live cluster state and re-applies Git state if it detects drift, even if no new commit arrived.
- **App-of-Apps:** A pattern where one root Application points to a directory of other Application manifests. The root syncs child Applications into the cluster, which then each manage their own workloads.
- **Desired state:** What Git says the cluster should look like.
- **Live state:** What the Kubernetes API server reports the cluster actually looks like.
- **OutOfSync:** The diff between desired and live state is non-empty. Doesn't always mean broken — could be intentional drift or a pending manual approval.
- **Resource hook:** An annotation (`argocd.argoproj.io/hook`) that marks a resource as a sync lifecycle hook rather than a persistent cluster resource.

---

## Interview Talking Points

> "At our last shop we were running vLLM endpoints for a dozen different model versions across two GPU clusters, and the deploy process was a mess — engineers SSHing into the CI box, running apply scripts, half the time the script had stale kubeconfig. We moved everything to Argo CD with an app-of-apps layout, one root app per cluster, child apps per model serving stack. The immediate win was audit: every config change is a PR, every PR has a reviewer, and the Argo CD UI shows you exactly which commit is live on which cluster. The bigger win was self-healing. We had a GPU node go OOM and the kubelet evict our RayService pod. Before GitOps, that meant a 4am page. After, Argo CD detected the drift inside three minutes and reconciled it. The on-call team didn't even know it happened until the morning standup. Sync waves also solved our operator-before-CR ordering problem — we'd had flaky deployments where the KubeRay operator wasn't ready when the RayCluster CR landed, so the CR would be ignored. Wave 0 for the operator, wave 1 for the CR, problem gone. We also locked down team access with AppProjects so the NLP team couldn't accidentally deploy into the CV team's namespace, which had actually happened twice before."

---

## Exercises

### Exercise 1: Install Argo CD on Local K8s

Get a working Argo CD instance on your local cluster (kind, k3s, or minikube).

```bash
# Create the argocd namespace and install Argo CD
kubectl create namespace argocd

kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for all pods to be ready
kubectl wait --for=condition=Ready pod --all -n argocd --timeout=120s

# Expose the UI on localhost:8080
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# Retrieve the initial admin password
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d; echo

# Login via CLI
argocd login localhost:8080 \
  --username admin \
  --password $(kubectl get secret argocd-initial-admin-secret -n argocd \
    -o jsonpath="{.data.password}" | base64 -d) \
  --insecure
```

Verify:
```bash
kubectl get pods -n argocd
# Expected: argocd-server, argocd-repo-server, argocd-application-controller,
#           argocd-applicationset-controller, argocd-dex-server all Running
```

---

### Exercise 2: Deploy an App from Git (App-of-Apps Pattern)

Create a root Application that points to a directory of child Application manifests. This mirrors how a real HPE platform repo would be structured.

Assume your Git repo has this layout:
```
mlops-infra/
  apps/
    root-app.yaml         # the bootstrap application
    namespaces.yaml
    kuberay-operator.yaml
    vllm-serving.yaml
    observability.yaml
```

**`apps/root-app.yaml`** — the bootstrap Application you apply once by hand:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: hpe-mlops-root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/mlops-infra.git
    targetRevision: main
    path: apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

**`apps/vllm-serving.yaml`** — child Application for the vLLM serving stack:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: vllm-serving
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: hpe-inference
  source:
    repoURL: https://github.com/your-org/mlops-infra.git
    targetRevision: main
    path: manifests/vllm-serving
  destination:
    server: https://kubernetes.default.svc
    namespace: vllm-serving
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
```

Apply the root app and watch the cascade:
```bash
kubectl apply -f apps/root-app.yaml

# Watch Argo CD discover and sync all child apps
argocd app list
argocd app get hpe-mlops-root
```

---

### Exercise 3: Sync Waves — Deploy Operator Before App (KubeRay Example)

Without sync waves, the RayCluster CR lands on the cluster before the KubeRay operator has registered its CRD. The CR is rejected. Sync waves fix this by letting you declare order declaratively.

**`manifests/kuberay-operator/namespace.yaml`**:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kuberay-system
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
```

**`manifests/kuberay-operator/operator.yaml`** — wave 0, CRDs + operator:

```yaml
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: kuberay-operator
  namespace: kuberay-system
  annotations:
    argocd.argoproj.io/sync-wave: "0"
spec:
  chart: kuberay-operator
  repo: https://ray-project.github.io/kuberay-helm/
  version: "1.1.1"
  targetNamespace: kuberay-system
  valuesContent: |-
    image:
      repository: quay.io/kuberay/operator
      tag: v1.1.1
    resources:
      limits:
        cpu: 500m
        memory: 512Mi
```

**`manifests/kuberay-operator/raycluster.yaml`** — wave 1, the actual cluster:

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: hpe-inference-cluster
  namespace: kuberay-system
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  rayVersion: "2.9.3"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
          - name: ray-head
            image: rayproject/ray:2.9.3-gpu
            resources:
              limits:
                cpu: "4"
                memory: "16Gi"
                nvidia.com/gpu: "1"
  workerGroupSpecs:
    - replicas: 2
      minReplicas: 1
      maxReplicas: 4
      groupName: gpu-workers
      rayStartParams: {}
      template:
        spec:
          containers:
            - name: ray-worker
              image: rayproject/ray:2.9.3-gpu
              resources:
                limits:
                  cpu: "8"
                  memory: "32Gi"
                  nvidia.com/gpu: "2"
```

**`manifests/kuberay-operator/rayservice.yaml`** — wave 2, the vLLM serving endpoint:

```yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-llama3-service
  namespace: kuberay-system
  annotations:
    argocd.argoproj.io/sync-wave: "2"
spec:
  serviceUnhealthySecondThreshold: 300
  deploymentUnhealthySecondThreshold: 300
  serveConfigV2: |
    applications:
      - name: llama3-serve
        import_path: vllm_serve:deployment
        runtime_env:
          pip:
            - vllm==0.4.2
          env_vars:
            MODEL_ID: "meta-llama/Meta-Llama-3-8B-Instruct"
            HUGGING_FACE_HUB_TOKEN: "$(HF_TOKEN)"
        deployments:
          - name: VLLMDeployment
            num_replicas: 2
            ray_actor_options:
              num_gpus: 1
  rayClusterConfig:
    rayVersion: "2.9.3"
    headGroupSpec:
      rayStartParams:
        dashboard-host: "0.0.0.0"
      template:
        spec:
          containers:
            - name: ray-head
              image: rayproject/ray:2.9.3-gpu
              resources:
                limits:
                  cpu: "4"
                  memory: "16Gi"
    workerGroupSpecs:
      - replicas: 2
        groupName: gpu-workers
        rayStartParams: {}
        template:
          spec:
            containers:
              - name: ray-worker
                image: rayproject/ray:2.9.3-gpu
                resources:
                  limits:
                    cpu: "8"
                    memory: "32Gi"
                    nvidia.com/gpu: "2"
```

Verify the wave ordering during sync:
```bash
argocd app sync vllm-serving --watch
# You'll see wave -1 resources go Synced first, then wave 0 waits for Healthy,
# then wave 1, then wave 2.
```

---

### Exercise 4: ApplicationSet for Multi-Environment (Staging/Prod)

Instead of maintaining two separate Application manifests that are 95% identical, use an ApplicationSet with a list generator to stamp out both environments from one template.

**`apps/vllm-appset.yaml`**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: vllm-serving-environments
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: staging
            namespace: vllm-staging
            replicaCount: "1"
            gpuLimit: "1"
            revision: develop
          - env: prod
            namespace: vllm-prod
            replicaCount: "3"
            gpuLimit: "2"
            revision: main
  template:
    metadata:
      name: "vllm-serving-{{env}}"
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: hpe-inference
      source:
        repoURL: https://github.com/your-org/mlops-infra.git
        targetRevision: "{{revision}}"
        path: manifests/vllm-serving
        helm:
          parameters:
            - name: replicaCount
              value: "{{replicaCount}}"
            - name: resources.limits.nvidia\\.com/gpu
              value: "{{gpuLimit}}"
            - name: environment
              value: "{{env}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: "{{namespace}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

Apply and inspect:
```bash
kubectl apply -f apps/vllm-appset.yaml

argocd app list
# NAME                        STATUS  HEALTH   NAMESPACE
# vllm-serving-staging        Synced  Healthy  vllm-staging
# vllm-serving-prod           Synced  Healthy  vllm-prod

# Promote a change to prod: update the revision or parameter in the appset,
# commit, push. Argo CD handles the rest.
```

---

### Exercise 5: Rollback and Self-Heal Demo

**Part A — Rollback to a previous Git revision:**

```bash
# Check the history of an application
argocd app history vllm-serving

# ID  DATE                            REVISION
# 1   2026-08-20 09:14:32 +0000 UTC   main (a3f9c21)
# 2   2026-08-25 14:02:11 +0000 UTC   main (b7d4e88)  <-- current

# Roll back to revision 1 (this disables auto-sync temporarily)
argocd app rollback vllm-serving 1

# Verify the running revision
argocd app get vllm-serving | grep -E "Revision|Status"
```

**Part B — Self-heal demo:**

Enable auto-sync with self-heal on the app (if not already set):
```bash
argocd app set vllm-serving \
  --sync-policy automated \
  --self-heal \
  --auto-prune
```

Now simulate drift — delete a resource out-of-band:
```bash
# Delete the RayService directly (as if someone ran kubectl delete by mistake)
kubectl delete rayservice vllm-llama3-service -n kuberay-system

# Watch Argo CD detect and repair it (within the refresh interval, default 3m)
# Speed it up with a manual refresh:
argocd app get vllm-serving --refresh

# Within seconds you'll see:
argocd app get vllm-serving | grep -E "Health|Sync"
# Health Status:  Healthy
# Sync Status:    Synced

kubectl get rayservice -n kuberay-system
# NAME                   SERVICE STATUS   NUM SERVE ENDPOINTS
# vllm-llama3-service    Running          2
```

The resource is back. No human intervention. This is what self-healing looks like in practice.

---

### Exercise 6: RBAC + AppProject for Team Isolation

Two teams share the same cluster: the **NLP team** owns `vllm-serving` and `kuberay-system`. The **Platform team** owns everything else. Use AppProjects to enforce the boundary.

**`manifests/argocd-config/appproject-nlp.yaml`**:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: nlp-team
  namespace: argocd
spec:
  description: "NLP team — vLLM serving and KubeRay workloads"

  # Only this repo can be used as source
  sourceRepos:
    - https://github.com/your-org/mlops-infra.git
    - https://github.com/your-org/nlp-model-configs.git

  # Applications in this project can only deploy to these namespaces
  destinations:
    - namespace: vllm-serving
      server: https://kubernetes.default.svc
    - namespace: kuberay-system
      server: https://kubernetes.default.svc
    - namespace: vllm-staging
      server: https://kubernetes.default.svc
    - namespace: vllm-prod
      server: https://kubernetes.default.svc

  # Block deploying cluster-scoped resources (no RBAC, no CRDs from this project)
  clusterResourceWhitelist: []

  # Namespace-scoped resources allowed
  namespaceResourceWhitelist:
    - group: "ray.io"
      kind: RayCluster
    - group: "ray.io"
      kind: RayService
    - group: "apps"
      kind: Deployment
    - group: ""
      kind: Service
    - group: ""
      kind: ConfigMap
    - group: ""
      kind: Secret
    - group: "autoscaling"
      kind: HorizontalPodAutoscaler
    - group: "networking.k8s.io"
      kind: Ingress

  # RBAC roles within this project
  roles:
    - name: nlp-developer
      description: Can sync and view apps in the nlp-team project
      policies:
        - p, proj:nlp-team:nlp-developer, applications, get, nlp-team/*, allow
        - p, proj:nlp-team:nlp-developer, applications, sync, nlp-team/*, allow
        - p, proj:nlp-team:nlp-developer, applications, override, nlp-team/*, allow
      groups:
        - your-org:nlp-engineers

    - name: nlp-readonly
      description: Read-only access for stakeholders
      policies:
        - p, proj:nlp-team:nlp-readonly, applications, get, nlp-team/*, allow
      groups:
        - your-org:nlp-stakeholders
```

**`manifests/argocd-config/argocd-rbac-cm.yaml`** — cluster-level RBAC:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    # Platform admins get full access
    p, role:platform-admin, applications, *, */*, allow
    p, role:platform-admin, clusters, *, *, allow
    p, role:platform-admin, repositories, *, *, allow
    p, role:platform-admin, projects, *, *, allow

    # NLP engineers can only operate within their project
    p, role:nlp-engineer, applications, get, nlp-team/*, allow
    p, role:nlp-engineer, applications, sync, nlp-team/*, allow
    p, role:nlp-engineer, applications, override, nlp-team/*, allow

    g, your-org:platform-admins, role:platform-admin
    g, your-org:nlp-engineers, role:nlp-engineer
  scopes: "[groups]"
```

Apply and verify:
```bash
kubectl apply -f manifests/argocd-config/appproject-nlp.yaml
kubectl apply -f manifests/argocd-config/argocd-rbac-cm.yaml

# Confirm the project exists
argocd proj get nlp-team

# Try creating an Application that targets a disallowed namespace (should fail)
argocd app create bad-app \
  --project nlp-team \
  --repo https://github.com/your-org/mlops-infra.git \
  --path manifests/some-other-service \
  --dest-namespace platform-system \
  --dest-server https://kubernetes.default.svc
# Expected: FATA[...] application destination {... platform-system} is not permitted
```

---

## References

- [Argo CD Official Documentation](https://argo-cd.readthedocs.io/en/stable/)
- [Argo CD Application CRD Reference](https://argo-cd.readthedocs.io/en/stable/operator-manual/application.yaml)
- [ApplicationSet Controller Docs](https://argocd-applicationset.readthedocs.io/en/stable/)
- [Sync Waves and Hooks](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [AppProject RBAC](https://argo-cd.readthedocs.io/en/stable/user-guide/projects/)
- [KubeRay Helm Chart](https://github.com/ray-project/kuberay-helm)
- [vLLM Documentation](https://docs.vllm.ai/en/latest/)
- [GitOps Principles — OpenGitOps](https://opengitops.dev/)
- [Argo CD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)

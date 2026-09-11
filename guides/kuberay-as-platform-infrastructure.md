# KubeRay as Platform Infrastructure

**Summary:** Yes - KubeRay prepares and operates the infrastructure a Ray application runs on, and nothing above that. This guide explains what its three CRDs actually own, where the boundary sits between "Ray infrastructure" and "your platform", and how it slots into an on-prem LLM-as-a-Service stack alongside MLflow, Argo and vLLM.

## The One-Sentence Answer

KubeRay is a Kubernetes operator that turns "I need a Ray cluster" into a declarative object. It owns cluster lifecycle - scheduling head and worker pods, wiring them together, scaling them, upgrading them, and tearing them down. It does **not** own your model, your data, your API contract, or your release process. It is the compute substrate, not the platform.

That distinction is the whole reason it composes well. KubeRay does one layer properly and leaves the others to tools that do them properly.

## Three CRDs, Three Jobs

Almost every design mistake with KubeRay is picking the wrong CRD, so start here.

| CRD | Owns | Lifecycle | Reach for it when |
| --- | --- | --- | --- |
| `RayCluster` | Head + worker groups, `rayStartParams`, autoscaler config | Lives until you delete it | Interactive work, a shared cluster, or something else drives submission |
| `RayJob` | A job, and optionally a throwaway cluster for it | Runs to completion, can delete its own cluster | Batch, pipelines, CI - anything with an end |
| `RayService` | A `RayCluster` **plus** Serve apps, health checks and upgrades | Long-running, upgraded in place or by cluster swap | Production inference endpoints |

`RayCluster` is the primitive; the other two wrap it. A `RayJob` can create a cluster, run, and delete it via `deletionStrategy`/TTL, or target an existing one with `ClusterSelector`. A `RayService` manages one or more clusters and layers serving concerns on top.

The practical rule: **if it has an end, it is a `RayJob`; if it answers requests, it is a `RayService`; if neither fits, you probably want a plain `RayCluster` and something else driving it.**

## What RayService Adds Over RayCluster

This is the part worth understanding before designing a rollout, because it determines whether a model update costs you an outage or a second copy of your GPUs.

`RayService` supplies the Serve application graph through `serveConfigV2` and then maintains an **active** cluster. On an upgrade it stands up a **pending** cluster with the new spec, waits for it to become healthy, shifts traffic, and only then deletes the old one after `rayClusterDeletionDelaySeconds`.

What triggers which path matters enormously:

| Change | Result |
| --- | --- |
| `serveConfigV2` | Applied **in place**. No new cluster. |
| `rayClusterConfig` (image, `rayVersion`, resources) | **New cluster**, zero-downtime swap |
| `replicas`, `minReplicas`, `maxReplicas`, `scaleStrategy.workersToDelete` | Nothing - these are autoscaler-owned and explicitly excluded |

That last row is the one that surprises people: the autoscaler mutates the same CR the operator reconciles, so those fields are carved out to stop routine scaling from triggering an endless cluster-replacement loop.

`spec.upgradeStrategy.type` selects the behaviour - `NewCluster`, `NewClusterWithIncrementalUpgrade`, or `None`. The incremental path shifts traffic gradually using Gateway API `HTTPRoute` weights and requires the autoscaler to be enabled. Check whether your operator build actually has it: the `RayServiceIncrementalUpgrade` feature gate is **off** in a stock KubeRay 1.5.0.

> Budget for the swap. A `NewCluster` upgrade means both clusters exist simultaneously. With 70B-class models on H200s, that is briefly double the GPUs - which is exactly what `maxSurgePercent` and `stepSizePercent` exist to bound.

## Autoscaling - and Why Not HPA

Ray runs its own autoscaler as a sidecar in the head pod when `enableInTreeAutoscaling: true`. It watches **logical Ray demand** - pending tasks, actors and placement groups - and edits `replicas` on the worker groups, bounded by `minReplicas`/`maxReplicas`. The operator then reconciles pods.

HPA is the wrong tool here for two concrete reasons:

1. **Wrong signal.** HPA scales on CPU/memory. A Ray worker holding an idle actor or a pinned object looks busy to Ray and idle to HPA, and vice versa. Utilisation is not demand.
2. **No say in the victim.** HPA sets a replica count and lets the ReplicaSet choose what dies. Ray must choose - it knows which node holds live actors or unreplicated objects. It signals this through `scaleStrategy.workersToDelete`, a concept HPA has no equivalent for.

Use `autoscalerOptions.version: v2` for the safer draining behaviour.

## GPUs

GPUs are requested through the pod template's container **limits**:

```yaml
workerGroupSpecs:
  - groupName: h200
    replicas: 1
    template:
      spec:
        nodeSelector:
          accelerator: h200
        containers:
          - name: ray-worker
            resources:
              limits:
                nvidia.com/gpu: 1
```

Three things to internalise:

- KubeRay reads **limits**, not requests, and derives `--num-gpus` from them. Set requests equal to limits and let it infer.
- Override only via `rayStartParams.num-gpus`, which must be a **string** (`"1"`, not `1`). Needing the override usually means something upstream is wrong.
- The NVIDIA device plugin or GPU Operator is what advertises `nvidia.com/gpu` in the first place. No plugin, no schedulable GPUs, regardless of what KubeRay asks for.

For a heterogeneous fleet - H200 NVL alongside L40S - **use one worker group per accelerator class**, each with its own `nodeSelector`/affinity and tolerations. One group spanning both types gives Ray a resource pool it believes is fungible and isn't, and you get a 70B model sharded onto an L40S that cannot hold it.

## Serving vLLM on Top

Ray Serve LLM wraps vLLM and exposes an OpenAI-compatible surface. The parallelism knobs are where platform decisions live:

- `world_size = tensor_parallel_size * pipeline_parallel_size`
- `--distributed-executor-backend ray` is required for **multi-node** execution. Single-node multi-GPU can use multiprocessing and usually should.
- `placement_group_config` controls where the GPU workers land. **PACK** keeps tensor-parallel ranks on one node to minimise cross-node traffic; **SPREAD** distributes them.

Tensor parallelism is latency-sensitive and chatty. Keep a TP group inside one node and inside NVLink wherever the model fits; reach across nodes only when it does not. Whether `accelerator_type` says `H200` or `L40S` changes that answer.

## Where the Platform Boundary Sits

This is the part the CRDs do not tell you. On a stack of MLflow + SeaweedFS + Argo + KubeRay + vLLM, responsibilities divide cleanly:

| Concern | Owner | Not KubeRay because |
| --- | --- | --- |
| Which model version is live | MLflow registry | KubeRay has no concept of a model |
| Model weights at rest | SeaweedFS / S3 | Pods pull artifacts; the operator does not manage them |
| Rollout trigger and approval | Argo CD / GitHub Actions | KubeRay reconciles a CR, it does not decide when it should change |
| Pipeline orchestration | Argo Workflows | Argo creates `RayJob` CRs; Ray runs them |
| Compute lifecycle | **KubeRay** | This is the whole job |
| Request routing, TLS, quotas | nginx Ingress / gateway | Serve exposes an endpoint; it is not your edge |
| Identity and tenancy | Okta + K8s RBAC | Ray has no user model |

The integration points are narrow and boring, which is the goal:

- **MLflow → KubeRay.** MLflow registers and promotes; CI patches `serveConfigV2` or `rayClusterConfig` with the new model URI. Prefer object storage over the MLflow artifact store for large LLM weights - pulling tens of gigabytes through a tracking server is a bad time.
- **Argo Workflows → KubeRay.** A workflow step creates a `RayJob` CR (or calls the Jobs API through `HTTPMode`) and waits. Embeddings, batch inference and evaluation all fit this shape.
- **Argo CD → KubeRay.** The `RayService` CR lives in Git. Changing the model means a commit, which makes rollback a revert.

## Multi-Tenancy: Shared or Dedicated

Both work. KubeRay happily runs many clusters, on different Ray versions, in one Kubernetes cluster.

| | Dedicated cluster per tenant | Shared cluster |
| --- | --- | --- |
| Isolation | Strong - separate GCS, separate failure domain | Weak - a bad actor affects neighbours |
| GPU efficiency | Worse - stranded capacity per tenant | Better - one pool |
| Version freedom | Per-tenant Ray versions | Everyone moves together |
| Blast radius | One tenant | Everyone |

For GPU inference the calculus usually favours **dedicated clusters per model or tenant**, because a head-node failure takes down everything attached to it and stranded GPU capacity is cheaper than a shared outage. Use namespaces plus `ResourceQuota` and RBAC either way.

Expose submission through `RayJob` rather than handing out cluster access. It is declarative, auditable, and it keeps the Kubernetes API as your permission boundary instead of the Ray dashboard.

## Production Pitfalls

**The head node is a single point of failure.** The GCS - Ray's global control store - is in-memory on the head by default. Lose the head and the cluster's control-plane state goes with it; workers cannot re-join and get torn down.

Back it with external Redis for GCS fault tolerance so a head restart is recoverable. But be precise about what that buys: **GCS persistence recovers control-plane metadata only.** Actor in-memory state and the object store are still not durable. Applications that need durability must checkpoint to external storage themselves.

The same caveat applies to `suspend`: it deletes pods, so it is a cold stop. The object store, live actors and job history are gone.

**Observability.** Scrape with **PodMonitor**, not ServiceMonitor, for head and worker pods - `RayService` creates two services and a ServiceMonitor on the head double-counts. The operator exposes `kuberay_*` metrics (`kuberay_cluster_info`, `kuberay_service_condition_ready`, `kuberay_cluster_provisioned_duration_seconds`) which are the right signals for platform-level alerting, distinct from Ray's own workload metrics. Ray ships Grafana dashboard JSON.

**Feature gates.** Check them before designing around a capability. Stock KubeRay 1.5.0 ships `RayServiceIncrementalUpgrade=false` and `RayJobDeletionPolicy=false`.

## So: Is It Infrastructure Prep?

Yes, and the framing is useful. Treat KubeRay the way you treat a database operator - it makes a stateful distributed system declarative, schedulable and upgradable on Kubernetes. It gives you a well-defined seam (`RayJob` for batch, `RayService` for serving) that the rest of the platform integrates against.

What it will not do is make the decisions above that seam. Which model is live, who may call it, what happens when it regresses, where the weights come from, and what the rollout looks like - those stay yours. KubeRay's value is that it removes the *cluster* from that list.

## See Also

- [Lab 12 - KubeRay RayCluster Quickstart on Rancher Desktop](../k8s/labs/12-kuberay-raycluster-quickstart/README.md) - verified hands-on install and job submission
- [Lab 08 - Distributed Inference with KubeRay](../mlops-infra/08-kuberay-distributed-inference/README.md) - RayService, vLLM tensor parallelism, autoscaling, Argo CD integration

## References

- [KubeRay CRD API reference](https://docs.ray.io/en/latest/cluster/kubernetes/references/api.html)
- [RayService quickstart](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/rayservice-quick-start.html)
- [RayService incremental upgrades](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/rayservice-incremental-upgrade.html)
- [Configuring KubeRay autoscaling](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/configuring-autoscaling.html)
- [Ray autoscaler vs Kubernetes autoscaling](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/k8s-autoscaler.html)
- [Using GPUs with KubeRay](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/gpu.html)
- [RayCluster configuration](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/config.html)
- [GCS fault tolerance](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/kuberay-gcs-ft.html)
- [Prometheus and Grafana integration](https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/prometheus-grafana.html)
- [KubeRay metrics reference](https://docs.ray.io/en/latest/cluster/kubernetes/k8s-ecosystem/metrics-references.html)
- [Ray Serve LLM architecture](https://docs.ray.io/en/latest/serve/llm/architecture/overview.html)
- [Ray Serve LLM configuration](https://docs.ray.io/en/latest/serve/llm/user-guides/configuration.html)
- [vLLM parallelism and scaling](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- [Ray Serve model registries (MLflow)](https://docs.ray.io/en/latest/serve/model-registries.html)

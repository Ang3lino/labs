# KubeRay on kind (Apple Silicon) — Learning Guide

> What tripped me up, explained so it doesn't again.

Running the KubeRay `ray-job.sample.yaml` on a local kind cluster, why it sat
`Pending` for 15 minutes, and what the operator is actually doing underneath.

## Local cluster on a Mac

```bash
brew install kind
kind create cluster
```

kind needs a container runtime. Docker Desktop, Colima, Podman, or Rancher Desktop all work.

### Rancher Desktop specifics

Works, **but only with the `dockerd (moby)` engine**, not containerd.

- Preferences → Container Engine → `dockerd (moby)` → restart. `docker ps` works → kind works.
- On containerd you'd need `KIND_EXPERIMENTAL_PROVIDER=nerdctl kind create cluster` (experimental, flakier).
- Rancher ships its own k3s cluster. If you only want kind, turn it off — otherwise two clusters
  compete for the same VM cores:

```bash
rdctl set --kubernetes.enabled=false
```

kind creates its own kubeconfig context (`kind-kind`), so contexts never collide.

## The failure: pods Pending forever

```
NAME                                           READY   STATUS     RESTARTS   AGE
rayjob-sample-6lqns-head-jbv5d                 0/1     Pending    0          12m
rayjob-sample-6lqns-small-group-worker-846sc   0/1     Init:0/1   0          12m
```

**`Pending` has exactly one meaning: the pod has not been assigned to a node.** Not crashing,
not pulling — never placed. So there is only one component to interrogate: the scheduler. Its
verdict is always in the Events at the bottom of `describe`.

```bash
kubectl describe pod <pod> | grep -A 5 -i event
```
```
Conditions:
  Type           Status
  PodScheduled   False        ← not placed on any node

Events:
  Warning  FailedScheduling  2m29s (x3 over 12m)  default-scheduler
  0/1 nodes are available: 1 Insufficient cpu.
```

That is the root cause verbatim. `0/1 nodes` = one node checked, one rejected. No inference needed.

### Turning "insufficient" into numbers

Three facts — **supply**, **already spoken for**, **demand**:

```bash
# supply
kubectl get node kind-control-plane -o jsonpath='{.status.allocatable.cpu}'
# → 2                                 (2000m)

# already requested by system pods
kubectl describe nodes | grep -A 10 "Allocated resources"
# → cpu  1250m (62%)                  (1250 being 62% confirms the 2000m denominator)

# demand
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].resources}'
# → req={"cpu":"1","memory":"2Gi"}    (1000m)
```

2000 − 1250 = **750m free. Head wants 1000m.** Doesn't fit.

> **The load-bearing detail:** the scheduler packs by `requests`, never by `limits` and never by
> actual usage. A node at 3% CPU will still reject the pod. Requests are a reservation, not a
> measurement.

### Why the worker showed a different symptom

The worker sat at `Init:0/1`, not `Pending` — but it was the same bug. Its init container
`wait-gcs-ready` blocks until the head's Ray GCS answers on 6379. Head never scheduled → GCS
never listened → init spun forever. **Two symptoms, one cause.** Fixing the head fixed both.

## Right-sizing the VM

A kind "node" is just a container, and a container reports the CPU count of the kernel it runs
on. On a Mac that kernel is inside the Rancher Desktop / Docker Desktop VM — not macOS. So
`2 cpus` was never a kind or k8s setting; it was the VM allocation showing through.

```bash
sysctl -n hw.ncpu hw.memsize              # host: 8 cores / 16 GB → room to give
rdctl list-settings | grep -A 5 virtualMachine
# "memoryInGB": 4, "numberCPUs": 2        ← the actual ceiling
```

`rdctl` is Rancher Desktop's CLI (`~/.rd/bin/rdctl`) — same settings store as the Preferences
GUI. `rdctl set` writes the config and reconfigures the VM in place; Docker came back in ~10s
and the kind container survived.

```bash
rdctl set --virtual-machine.number-cpus 6 --virtual-machine.memory-in-gb 10
```

Sizing math for this sample:

| | cpu request |
|---|---|
| system pods | 1250m |
| ray head | 1000m |
| ray worker | 200m |
| **total** | **~2.5 cores** |

So 2 cores could never work; 4 is comfortable, 6 leaves headroom. Memory followed the same
logic — the head requests 2Gi with a 5Gi limit plus a 5Gi `/dev/shm` emptyDir, so 4 GB would
have bitten right after the CPU fix.

**Gotcha**: after the VM restart the kind API server port is briefly unreachable
(`connection refused` on `127.0.0.1:<port>`). Wait, don't recreate the cluster.

## How KubeRay actually works

One object in, six out:

```
kubectl apply  →  RayJob "rayjob-sample"          ← the ONLY thing you wrote
                       │
   kuberay-operator watches rayjobs.ray.io and reconciles:
                       │
                       ├─ RayCluster  rayjob-sample-6lqns      (generated name)
                       │     ├─ Pod   ...-head-jbv5d           head: GCS + dashboard
                       │     ├─ Pod   ...-small-group-worker-846sc
                       │     └─ Svc   ...-head-svc             6379/8265/10001/8080
                       ├─ Job         rayjob-sample            submitter: runs `ray job submit`
                       │     └─ Pod   rayjob-sample-bb2z8      → Completed
                       └─ writes status back: jobStatus: SUCCEEDED
```

Installing KubeRay adds four CRDs — `rayclusters`, `rayjobs`, `rayservices`, `raycronjobs` —
which teach the API server four new nouns. The **kuberay-operator** Deployment is a control
loop that watches those nouns and makes reality match. Nothing is magic; a Go program issues
the pod/service/job creates you'd otherwise write by hand.

That's why the head pod has env vars you never wrote — `RAY_CLUSTER_NAME`,
`KUBERAY_GEN_RAY_START_CMD`, `RAY_PORT`, plus the worker's `wait-gcs-ready` init container.
**Essentially everything in `kubectl describe` was synthesized, not authored** — which is also
why the `FailedScheduling` line takes some scrolling to reach.

### Picking the right noun

| CRD | For | Lifecycle |
|---|---|---|
| `RayCluster` | long-lived cluster you attach to | you delete it |
| `RayJob` | run this script, then stop | cluster dies with the job (if enabled) |
| `RayService` | online inference (Ray Serve) | permanent, rolling-upgrade aware |
| `RayCronJob` | scheduled batch | recurring RayJobs |

## Anatomy of the sample

[`ray-job.sample.yaml`](https://raw.githubusercontent.com/ray-project/kuberay/v1.7.0/ray-operator/config/samples/ray-job.sample.yaml)
is two YAML documents: a `RayJob` and a `ConfigMap` holding the Python.

```yaml
entrypoint: python /home/ray/samples/sample_code.py
runtimeEnvYAML: |
  pip: [requests==2.26.0, pendulum==2.1.2]
  env_vars: { counter_name: "test_counter" }
```

`runtimeEnvYAML` makes Ray pip-install those pins at runtime and inject the env var — which is
why the job takes a minute even after pods are `Running`.

| | image | requests | limits |
|---|---|---|---|
| head | `rayproject/ray:2.52.0` | cpu 1, mem 2Gi | cpu 1, mem 5Gi |
| worker ×1 | `rayproject/ray:2.52.0` | cpu 200m | cpu 1 |

### The Python, and the Ray add-ons in it

Pulled straight from the running cluster:

```bash
kubectl get configmap ray-job-code-sample -o jsonpath='{.data.sample_code\.py}'
```

```python
import ray
import os
import requests

ray.init()

@ray.remote
class Counter:
    def __init__(self):
        # Used to verify runtimeEnv
        self.name = os.getenv("counter_name")
        assert self.name == "test_counter"
        self.counter = 0

    def inc(self):
        self.counter += 1

    def get_counter(self):
        return "{} got {}".format(self.name, self.counter)

counter = Counter.remote()

for _ in range(5):
    ray.get(counter.inc.remote())
    print(ray.get(counter.get_counter.remote()))

# Verify that the correct runtime env was used for the job.
assert requests.__version__ == "2.26.0"
```

Strip the Ray bits and it's an ordinary class incremented five times. Everything that makes it
distributed is an add-on layered on top of plain Python:

| Add-on | What it does |
|---|---|
| `ray.init()` | Connects to the cluster. Inside a KubeRay pod it reads the operator-injected `RAY_ADDRESS` and **joins the existing cluster** — it does not start a local one. Same line on your laptop spins up a single-node Ray instead, which is why the script is portable unchanged. |
| `@ray.remote` on a **class** | Turns it into an **Actor** — a stateful process living on some node, holding `self.counter` across calls. On a **function** it would create a stateless **Task** instead. That's the whole API surface: tasks for stateless work, actors for stateful. |
| `Counter.remote()` | Not `Counter()`. Asks the Ray scheduler to place an actor process somewhere in the cluster and returns an **ActorHandle immediately** — the constructor may not have run yet. |
| `counter.inc.remote()` | Not `counter.inc()`. Sends the method call to wherever that actor lives and returns an **ObjectRef** (a future) immediately. Non-blocking. |
| `ray.get(ref)` | **Blocks** and pulls the value out of Ray's distributed object store. This is the only synchronization point in the script. |

The `.remote()` suffix is the seam between local and distributed. Forget it and you silently
call a plain method on a handle, which errors — a good thing, since the alternative would be
code that works locally and deadlocks in the cluster.

> **Gotcha — the object store is that `/dev/shm` mount.** The `shared-mem` emptyDir with
> `Medium: Memory, SizeLimit: 5Gi` in the pod spec isn't incidental; it *is* Ray's shared-memory
> object store, where `ray.get` reads from. Undersize it and you get spilling to disk or
> out-of-memory kills on large objects. It's the one volume you should size deliberately.

> **Gotcha — actor CPU defaults.** Tasks default to `num_cpus=1`. Actors default to **1 CPU for
> scheduling but 0 for running**, so an unbounded number of actors can pile onto one node once
> placed. Pin it explicitly with `@ray.remote(num_cpus=2)` when it matters — and remember this is
> Ray's accounting, entirely separate from the k8s `requests` the scheduler uses.

### The two add-ons under test

The script is a smoke test for `runtimeEnvYAML`, and both asserts exist to make a silent failure
loud:

| Assert | Proves |
|---|---|
| `self.name == "test_counter"` | `env_vars` reached the **actor process on a worker pod** — not just the driver. Env propagation across the cluster works. |
| `requests.__version__ == "2.26.0"` | The `pip:` pins were installed into the job's runtime env at runtime, overriding whatever the base image ships. |

Together they verify the runtime-env machinery end to end. That verification is the entire point
of the sample — the counter itself computes nothing.

### Defaults and knobs worth knowing

Commented out in the sample, but they matter:

- `shutdownAfterJobFinishes` / `ttlSecondsAfterFinished` — both off, which is why the cluster
  pods keep running after `SUCCEEDED`. Deliberate, so you can read logs.
- `submissionMode` — defaults to `K8sJobMode`, which is where the extra `Completed` pod comes
  from: a throwaway submitter Job running `ray job submit`.
- `preRunningDeadlineSeconds: 300` — **would have failed the job at 5 minutes instead of letting
  it sit Pending for 15.** Worth enabling on a resource-constrained local cluster.
- `suspend` — gate cluster creation; used with queueing systems like Kueue.

### Reading it back

```bash
kubectl get rayjob rayjob-sample -o yaml | yq 'del(.status, .metadata.annotations)'
```

The `status` block is the useful half:

```yaml
jobStatus: SUCCEEDED
rayClusterName: rayjob-sample-6lqns
rayJobInfo: { startTime: 05:09:18, endTime: 05:09:42 }   # actual job: 24 seconds
startTime: 04:53:01                                       # RayJob created, 16 min earlier
desiredCPU: 1200m                                         # operator's own sum of requests
```

That gap is the whole debugging session: 16 minutes wall-clock, 24 seconds of compute.

## Mapping your own workload

**YAML = where and on what. Python = what.** The YAML never mentions your algorithm; the Python
never mentions pods. The seam is `entrypoint` plus a volume mount. `ray.init()` inside the pod
reads the operator-injected `RAY_ADDRESS` and joins the cluster that already exists around it.

Realistically you change **three things**:

```yaml
entrypoint: python /home/ray/samples/my_code.py   # 1. your script
runtimeEnvYAML: |                                  # 2. your deps
  pip: [pandas, scikit-learn]
```
```yaml
- replicas: 4                                      # 3. your scale + resources
  template:
    spec:
      containers:
      - name: ray-worker
        resources:
          requests: { cpu: "2", memory: "4Gi" }
```

Yes, it is copy-paste boilerplate — by design. The `config/samples/` directory exists for
exactly this; nobody writes a RayJob from memory.

### Skip the YAML entirely

KubeRay ships a kubectl plugin (`job`, `session`, `log`, `scale`, `get` subcommands):

```bash
kubectl krew install ray
kubectl ray job submit --working-dir . -- python my_code.py
```

Generates the RayJob, uploads your local directory, streams logs, cleans up. **Start here.**
Drop to YAML only when you need GPUs, node selectors, autoscaling policy, or custom images.

The sample's ConfigMap trick (Python inlined into YAML) is a demo convenience — it caps around
1 MB and gets miserable fast. Real options: bake code into the image, or point `working_dir` at
S3/GCS.

## Why Ray on k8s

**It is not k8s instead of cloud.** Production Ray on AWS/GCP/Azure is overwhelmingly KubeRay on
EKS/GKE/AKS — same CRDs, same YAML, cloud nodes underneath. The proposition is **portability**:
one manifest runs on kind, on-prem, and EKS. Your laptop becomes a faithful-if-tiny rehearsal of
prod — `Insufficient cpu` on kind is the identical failure, from the identical command, as on EKS.

| Alternative | Why Ray instead |
|---|---|
| plain k8s Jobs | k8s schedules *containers* and has no idea what's inside. Shared state, work queues, retries, aggregation — all hand-rolled. Ray retries at *task* granularity; k8s can only restart a whole pod. |
| Spark / Dask | Spark wins on dataframes and SQL; it fights you when the unit of work is "a Python object holding GPU state." Ray's primitives are arbitrary Python. |
| `ray up` (VM launcher) | Per-cloud config, no self-healing, nothing reusable for the rest of your infra. |
| SageMaker / Vertex / AWS Batch | Less to operate, more lock-in, code grows vendor-shaped. |

### The honest cost

**Two schedulers, stacked, that do not talk to each other.**

```
KUBERAY_GEN_RAY_START_CMD: ray start --head --num-cpus=1 ...   ← Ray's logical CPUs
resources: requests: { cpu: "1" }                              ← k8s' physical reservation
```

Nothing enforces agreement. `num-cpus=8` with `requests.cpu=1` schedules 8 concurrent tasks into
one core's quota and throttles. **You own that consistency.** Add the Ray autoscaler and it's
three layers (Ray → k8s → cloud), three sets of timeouts. Debugging spans the Ray dashboard *and*
kubectl.

Worth it when the workload is genuinely distributed Python. Overkill when one beefy pod or a
plain k8s Job would do.

## Ray for LLMs

Arguably Ray's dominant use case today.

| Stage | Ray piece | What it buys |
|---|---|---|
| Batch inference | `ray.data.llm` | Score millions of rows through vLLM; streaming execution, auto-batching, spill to disk, worker retries |
| Online serving | `ray.serve.llm` | OpenAI-compatible endpoint, per-model autoscaling, multi-LoRA hot-swap |
| Fine-tuning | Ray Train | DeepSpeed/FSDP across nodes without torchrun launchers |
| HPO | Ray Tune | Sweep LRs / LoRA ranks across the cluster |
| RLHF | Ray core | verl and OpenRLHF are built on Ray — rollout + reward + train actors, one cluster |

**The thing only Ray does:** models too large for one node. Multi-node tensor parallelism needs a
distributed actor layer with collective communication, and **vLLM's own multi-node backend *is*
Ray** (`distributed_executor_backend="ray"`). Past ~70B on multiple boxes you're running Ray
whether you picked it or not.

Second: one cluster, all stages. Preprocess on CPU workers, fine-tune on GPU workers,
batch-score, serve — same cluster, same Python, no handoff between four systems.

### Current API shape

Batch:

```python
from ray.data.llm import build_llm_processor, vLLMEngineProcessorConfig

config = vLLMEngineProcessorConfig(model="meta-llama/Llama-3.1-8B-Instruct", concurrency=4)
processor = build_llm_processor(
    config,
    preprocess=lambda row: {"messages": [{"role": "user", "content": row["prompt"]}]},
    postprocess=lambda row: {"response": row["generated_text"]},
)
processor(ray.data.read_parquet("s3://bucket/prompts/")).write_parquet("s3://out/")
```

Serving:

```python
from ray.serve.llm import LLMConfig, build_openai_app

llm_config = LLMConfig(
    model_loading_config={"model_id": "llama-8b", "model_source": "meta-llama/Llama-3.1-8B-Instruct"},
    deployment_config={"autoscaling_config": {"min_replicas": 1, "max_replicas": 4}},
    engine_kwargs={"tensor_parallel_size": 2, "enable_prefix_caching": True},
)
app = build_openai_app({"llm_configs": [llm_config]})
```

> **Stale-API warning**: `mlops-infra/08-kuberay-distributed-inference` still uses
> `import_path: vllm.entrypoints.openai.api_server:build_app` on Ray 2.10. That was correct in
> 2024; `ray.serve.llm` has since replaced it, and the `autoscaling_config` keys drifted too.
> Reconcile before building those manifests.

## Apple Silicon reality check

```
node capacity: cpu 6, memory 10Gi     ← no nvidia.com/gpu
host: Apple M1 Pro, 16 GB
```

**No GPU, and kind on Apple Silicon can't get one** — no CUDA passthrough, and containers can't
reach the Metal GPU. A 1B model in fp16 on CPU inside a 10 GB VM generates a few tokens/sec.
Fine for proving plumbing, useless as a benchmark.

What is still worth doing locally:

1. **Shape validation** — run the `ray.serve.llm` topology with a tiny model (`Qwen2.5-0.5B`,
   CPU) and confirm the RayService lifecycle, the OpenAI endpoint, and the zero-downtime
   upgrade. The mechanics are identical at 70B; only the numbers change.
2. **Fake GPUs** — `k8s/labs/10-volcano-gpu-reservation` already advertises phantom
   `nvidia.com/gpu` as extended resources. Same trick makes GPU worker groups schedulable here,
   so autoscaler and placement-group logic can be exercised with no hardware.
3. **Real GPUs** — rent an EKS/GKE node or a single cloud GPU box. The manifest doesn't change,
   which is the whole portability argument.

## Command recap

```bash
# diagnose a Pending pod — Events name the constraint every time
kubectl describe pod <pod> | grep -A 5 -i event

# supply vs demand
kubectl get node <node> -o jsonpath='{.status.allocatable.cpu}'
kubectl describe nodes | grep -A 10 "Allocated resources"
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].resources}'

# resize the Rancher Desktop VM
rdctl list-settings | grep -A 5 virtualMachine
rdctl set --virtual-machine.number-cpus 6 --virtual-machine.memory-in-gb 10

# what the operator built from one object
kubectl get rayjob,raycluster,job,svc,pod
kubectl get rayjob <name> -o yaml | yq '.status'
```

## References

- [KubeRay docs](https://docs.ray.io/en/latest/cluster/kubernetes/index.html)
- [kubectl plugin](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/kubectl-plugin.html)
- [Ray Serve LLM](https://docs.ray.io/en/latest/serve/llm/serving-llms.html)
- [Ray Data LLM](https://docs.ray.io/en/latest/data/working-with-llms.html)
- [vLLM on KubeRay](https://docs.ray.io/en/latest/cluster/kubernetes/examples/vllm-rayservice.html)
- Lab: `mlops-infra/08-kuberay-distributed-inference`

# Lab 12 - KubeRay RayCluster Quickstart on Rancher Desktop

**Scenario:** The upstream Ray quickstart tells you to `kind create cluster` and, at the end, `kind delete cluster`. You are on Rancher Desktop, which has no such thing. Install KubeRay anyway, submit a real job to it, and learn the two traps that make the quickstart look broken when it isn't.

**No GPU required.** Everything here runs on a single-node CPU-only k3s VM.

## What You Learn

| Concept | Why it matters |
| --- | --- |
| KubeRay operator + `RayCluster` CRD | The operator is just Helm charts and CRDs - it does not care which distro you run |
| Head-first startup ordering | Why the worker sits in `Init:0/1` and the docs' next command fails |
| `kubectl wait` on a label selector | The difference between "the CR exists" and "the cluster is usable" |
| Ray Jobs API (`ray job submit`) | The submission path `RayJob` CRs use under the hood |
| Client/server version pinning | A mismatched `ray` CLI fails in ways that look like cluster bugs |
| `spec.suspend` | Releasing compute without destroying the declarative object |

**Interview signal:** *"I can stand up a Ray cluster on any Kubernetes distro and explain why the first three commands in the official quickstart appear to fail."*

## The Problem in One Paragraph

Every Ray-on-Kubernetes tutorial assumes `kind`, a throwaway cluster you create and delete per run. Real clusters are not disposable - Fort Collins is not getting `kind delete cluster`. The operator and the CRDs are completely distro-agnostic, so the *install* transfers unchanged; what does not transfer is the lifecycle. Swapping `kind delete cluster` for the right teardown, and learning to wait for readiness instead of assuming it, is the entire delta between the tutorial and something you would run twice.

## Prerequisites

```bash
kubectl version --client      # v1.28+
kubectl config current-context
helm version                  # v3
kubectl get nodes             # Rancher Desktop with Kubernetes enabled
```

> Raise the VM's memory and CPU in Rancher Desktop > Preferences > Virtual Machine first. The default allocation leaves Ray pods `Pending` forever, which looks like a scheduling bug and is actually a budget problem.

## kind vs Rancher Desktop - What Actually Differs

The upstream doc's cluster steps are the only part you replace.

| Upstream (`kind`) | Rancher Desktop | Why |
| --- | --- | --- |
| `kind create cluster` | already running | Rancher Desktop's k3s cluster is persistent, not per-run |
| `kind delete cluster` | `helm uninstall` + delete CRDs | You are removing a release, not a cluster |
| `killall kubectl` | `Stop-Process` / `taskkill` | No `killall` on Windows |
| upstream Kubernetes | k3s | Traefik, local-path storage and ServiceLB replace the upstream defaults |

KubeRay itself is unaffected - it ships as a Helm chart plus three CRDs and reconciles Pods like any other operator. The k3s differences only start to matter when you add Ingress, load balancing or storage around it.

## Step 1 - Install the Operator and a RayCluster

```bash
kubectl config use-context rancher-desktop
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update
helm install kuberay-operator kuberay/kuberay-operator --version 1.5.0
helm install raycluster kuberay/ray-cluster --version 1.5.0
```

Check what the operator advertises about itself:

```bash
kubectl get deploy kuberay-operator -o jsonpath='{.spec.template.spec.containers[0].args}'
```

Verified output (trimmed to the feature gates):

```
RayClusterStatusConditions=true,RayJobDeletionPolicy=false,RayMultiHostIndexing=false,RayServiceIncrementalUpgrade=false
```

Those gates tell you which CRD behaviours are live. `RayServiceIncrementalUpgrade=false` means the gradual traffic-shifting upgrade path is off in this build - worth knowing before you design a rollout around it.

## Step 2 - The Trap: It Is Not Ready When It Says It Exists

Run the status command immediately after install:

```bash
kubectl get rayclusters
```

Verified output at ~42s:

```
NAME                 DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS   AGE
raycluster-kuberay   1                                     2      3G       0               42s
```

`AVAILABLE WORKERS` and `STATUS` are **blank**. Following the tutorial's next command at this moment fails:

```
error: unable to forward port because pod is not running. Current status=Pending
```

Look at why:

```bash
kubectl get pods
```

Verified output during startup:

```
NAME                                          READY   STATUS     RESTARTS   AGE
kuberay-operator-dbfd4dbdd-9p26m              1/1     Running    0          2m7s
raycluster-kuberay-head-4qhml                 0/1     Running    0          109s
raycluster-kuberay-workergroup-worker-vj5kg   0/1     Init:0/1   0          109s
```

Two separate things are happening. The head is `Running` but `0/1` - its readiness probe has not passed because the Ray runtime is still booting. The worker is in `Init:0/1` because **its init container blocks until the head's GCS port answers**. This is deliberate head-first ordering: a worker has nothing to join until the head's global control store is up. Add a cold pull of the ~2 GB `rayproject/ray` image and the whole thing takes about 2m16s on a first run.

Wait properly instead of guessing:

```bash
kubectl wait --for=condition=Ready pod -l ray.io/cluster=raycluster-kuberay --timeout=300s
```

Verified output once settled:

```
NAME                                          READY   STATUS    RESTARTS   AGE
kuberay-operator-dbfd4dbdd-9p26m              1/1     Running   0          2m34s
raycluster-kuberay-head-4qhml                 1/1     Running   0          2m16s
raycluster-kuberay-workergroup-worker-vj5kg   1/1     Running   0          2m16s
```

```
NAME                 DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS   AGE
raycluster-kuberay   1                 1                   2      3G       0      ready    46m
```

The head log confirms it independently:

```
2026-09-11 13:33:32,443	SUCC scripts.py:1008 -- Ray runtime started.
```

## Step 3 - What the Operator Actually Generated

`kubectl describe` the head pod and read the command KubeRay built for you:

```
ray start --head --block --dashboard-agent-listen-port=52365 --dashboard-host=0.0.0.0 --memory=2000000000 --metrics-export-port=8080 --num-cpus=1
```

And the worker's:

```
ray start --address=raycluster-kuberay-head-svc.default.svc.cluster.local:6379 --block --dashboard-agent-listen-port=52365 --memory=1000000000 --metrics-export-port=8080 --num-cpus=1
```

This is the whole point of the operator. You declared a `RayCluster`; it derived `--num-cpus` and `--memory` from the container's resource limits (head `cpu: 1` / `memory: 2G`, worker `cpu: 1` / `memory: 1G`), wired the worker to the head Service by DNS, and opened the metrics port. The same derivation is how GPUs get advertised later - from limits, not requests.

## Step 4 - Reach the Dashboard

```bash
kubectl port-forward svc/raycluster-kuberay-head-svc 8265:8265
```

In a second shell:

```bash
curl http://localhost:8265/api/version
```

Verified output:

```
{"version": "4", "ray_version": "2.46.0", "ray_commit": "c3dd2ca0c2a24ddf327a213d2e936bd4eaa4ca0a", "session_name": "session_2026-09-11_13-33-16_277701_1"}
```

Note the `ray_version` - you need it in the next step.

## Step 5 - Install the `ray` CLI Without Installing Python

The tutorial assumes `ray` is on your PATH. On a fresh Windows box there is no Python at all:

```
Python was not found; run without arguments to install from the Microsoft Store
```

Do not install Python system-wide for this. `uv` will fetch its own interpreter and expose the CLI as a tool:

```bash
uv tool install "ray[default]==2.46.0" --python 3.11
uv tool update-shell        # puts ~/.local/bin on PATH; restart the shell
```

This installs three executables - `ray`, `serve`, `tune` - against a private CPython 3.11.

> Pin the version to the cluster's `ray_version` from Step 4. The Jobs API rejects or misbehaves across mismatched client/server versions, and the failures surface as runtime-env or dashboard errors that look like cluster faults. Upgrade later with `uv tool install "ray[default]==<new>" --force`.

## Step 6 - Submit a Job

With the port-forward still running:

```bash
ray job submit --address http://localhost:8265 -- python -c "import ray; ray.init(); print(ray.cluster_resources())"
```

Verified output:

```
Tailing logs until the job exits (disable with --no-wait):
2026-09-11 14:11:41,360	INFO job_manager.py:531 -- Runtime env is setting up.
2026-09-11 14:11:43,973	INFO worker.py:1554 -- Using address 10.42.0.53:6379 set in the environment variable RAY_ADDRESS
2026-09-11 14:11:43,974	INFO worker.py:1694 -- Connecting to existing Ray cluster at address: 10.42.0.53:6379...
2026-09-11 14:11:44,009	INFO worker.py:1879 -- Connected to Ray cluster. View the dashboard at 10.42.0.53:8265
{'memory': 3000000000.0, 'CPU': 2.0, 'node:10.42.0.54': 1.0, 'object_store_memory': 602298777.0, 'node:__internal_head__': 1.0, 'node:10.42.0.53': 1.0}

------------------------------------------
Job 'raysubmit_c67QGp4u3Hv9EerG' succeeded
------------------------------------------
```

`CPU: 2.0` is the whole cluster - 1 head plus 1 worker, matching the `--num-cpus=1` on each from Step 3. Two node entries confirm both pods joined.

The important detail is `RAY_ADDRESS` and the connection to `10.42.0.53:6379`: your `python -c` ran **on the cluster**, not on your laptop. `ray job submit` packaged it, shipped it to the head, and streamed the logs back. This is the Ray Jobs API, and it is the same submission path a `RayJob` CR drives - which is why Argo Workflows can create `RayJob` objects and get identical behaviour.

## Step 7 - Pause Instead of Deleting

You are done for the day but want the cluster back tomorrow. `spec.suspend` releases the pods while keeping the CR.

Git Bash takes the patch inline:

```bash
kubectl patch raycluster raycluster-kuberay --type merge -p '{"spec":{"suspend":true}}'
```

PowerShell mangles inline JSON, so assign it first:

```powershell
$patch = '{"spec":{"suspend":true}}'
kubectl patch raycluster raycluster-kuberay --type merge -p $patch
```

Escaping the quotes instead - the obvious first attempt - fails:

```
Error from server (BadRequest): error decoding patch: invalid character '\' looking for beginning of object key string
```

Verified output after suspending:

```
NAME                 DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS      AGE
raycluster-kuberay   1                                     2      3G       0      suspended   47m
```

Only the operator pod remains. Resume by patching `suspend` back to `false`.

Resuming has its own trap - `kubectl wait` fails outright if the operator has not created the pods yet:

```
error: no matching resources found
```

`kubectl wait` does not wait for a resource to *appear*, only for a condition on one that already exists. Poll for the pods first:

```bash
until [ "$(kubectl get pods -l ray.io/cluster=raycluster-kuberay --no-headers 2>/dev/null | wc -l)" -ge 2 ]; do sleep 5; done
kubectl wait --for=condition=Ready pod -l ray.io/cluster=raycluster-kuberay --timeout=300s
```

Verified output on resume - 39s this time, because the image is already cached:

```
pod/raycluster-kuberay-head-v6xhz condition met
pod/raycluster-kuberay-workergroup-worker-7z5jz condition met
```

> Suspend **deletes the pods**. The object store, live actors and job history are gone - it is a cold stop, not a VM-style pause. Leave the operator Deployment running; it is what reconciles `suspend: false` later.

## Break It On Purpose

| Experiment | What you should observe |
| --- | --- |
| `port-forward` before the head is Ready | `unable to forward port ... status=Pending` - the failure from Step 2 |
| Install a `ray` CLI on a different minor version | Submission fails on runtime-env or dashboard API differences, not on anything cluster-side |
| Suspend while a job is running | Job dies with the pods; nothing is checkpointed or resumed |
| `helm uninstall` then install a different KubeRay version without deleting CRDs | Schema conflicts from the leftover `ray.io` CRDs |
| Set worker `replicas` above the VM's CPU budget | Extra workers sit `Pending` on insufficient cpu, head stays healthy |
| Delete the head pod while a worker runs | Worker cannot re-join; GCS state was in-memory on the head |

## Teardown

Stop the port-forward first - there is no `killall` on Windows.

```powershell
Get-Job | Stop-Job; Get-Job | Remove-Job     # if you backgrounded it with Start-Job
Stop-Process -Name kubectl -Force            # or kill it by name
```

```bash
taskkill //F //IM kubectl.exe                # Git Bash needs the double slash
```

> A single slash makes MSYS rewrite `/F` into a Windows path before `taskkill` ever sees it.

Then remove the releases:

```bash
helm uninstall raycluster
helm uninstall kuberay-operator
kubectl get crd | grep ray.io
kubectl delete crd rayclusters.ray.io rayjobs.ray.io rayservices.ray.io
```

That last line is the one the upstream doc never needs. `kind delete cluster` destroys the CRDs along with the cluster; `helm uninstall` deliberately leaves them so an upgrade does not drop your custom resources. Leftovers collide with the next KubeRay version you install.

Nuclear options, rarely warranted here:

```powershell
rdctl factory-reset          # wipes k3s, images and settings
```

or Rancher Desktop > Troubleshooting > **Reset Kubernetes**, which resets the cluster but keeps images.

## Talking Points

- *"The KubeRay install is distro-agnostic because it's a Helm chart and three CRDs - what changes between kind and a real cluster is the lifecycle, not the install."*
- *"A RayCluster reporting blank STATUS isn't broken; the worker's init container is gating on the head's GCS port. Head-first ordering is the design."*
- *"`ray job submit` runs your code on the cluster via the Jobs API - the same path a RayJob CR uses, which is why pipelines integrate at that boundary."*
- *"`suspend` frees compute without destroying the declarative object, but it's a cold stop - anything in the object store or in live actors is lost."*
- *"I pin the Ray client to the cluster's version, because version skew shows up as runtime-env errors that look like infrastructure faults."*

## Where This Goes Next

- [KubeRay as Platform Infrastructure](../../../guides/kuberay-as-platform-infrastructure.md) - what the three CRDs are actually for, and where KubeRay sits in a full inference platform
- [Lab 08 - Distributed Inference with KubeRay](../../../mlops-infra/08-kuberay-distributed-inference/README.md) - RayService, vLLM tensor parallelism and autoscaling on top of this foundation

## References

- [KubeRay RayCluster Quickstart](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/raycluster-quick-start.html)
- [KubeRay CRD API reference](https://docs.ray.io/en/latest/cluster/kubernetes/references/api.html)
- [Ray Jobs CLI](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/index.html)
- [RayCluster configuration guide](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/config.html)
- [KubeRay v1.5.0 release notes](https://github.com/ray-project/kuberay/releases/tag/v1.5.0)
- [Rancher Desktop docs](https://docs.rancherdesktop.io/)

---
**Verification status:** every step in this lab was executed end-to-end on k3s (Rancher Desktop, single node) with KubeRay 1.5.0 and Ray 2.46.0 on 2026-09-11. All outputs shown are real, including the two failures in Steps 2 and 7. GPU scheduling, multi-node worker groups, `RayService` and vLLM are **not covered here** - the test machine is single-node and CPU-only; see lab 08 for those.

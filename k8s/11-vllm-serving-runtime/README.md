# Lab 11 — Choosing an LLM Serving Runtime (vLLM on Kubernetes)

**Scenario:** Your platform team must pick ONE serving runtime — vLLM, NVIDIA NIM, Triton, or TensorRT-LLM. Every downstream decision (engine flags, metric names, batching, packaging) is pinned to that choice. Everyone "just assumes vLLM." Your job is to make the assumption into a decision by testing the criteria that actually matter.

**No GPU required for Parts A and B.** Part C needs one and is marked clearly.

## What You Learn

| Concept | Why it matters |
| --- | --- |
| Runtime vs. orchestration layer | KServe and Ray Serve are alternatives to *each other*, not to vLLM |
| OpenAI-compatible surface | Whether your gateway needs an adapter, and what that costs |
| Prometheus metric names | TTFT, queue depth, KV cache — showback and autoscaling depend on these existing |
| Continuous batching | Why throughput on bursty traffic isn't about raw FLOPs |
| PagedAttention / KV cache | The memory maths that decides how many users fit on one card |
| Tensor parallelism vs. interconnect | Why TP=2 without NVLink is a capacity trick, not a speed-up |

**Interview signal:** *"I evaluated four inference runtimes against written criteria and can explain why the winner won on a specific hardware profile."*

## The Stack — Get This Straight First

The single most common confusion in this space:

```
Kubernetes              schedules Pods, knows nothing about models
  └─ KubeRay            operator: RayCluster / RayService CRDs
      └─ Ray Serve      replicas, autoscaling, request routing   <- ORCHESTRATION
          └─ vLLM       loads weights, batches, generates tokens <- EXECUTION
              └─ GPU
```

| Layer | Examples | Question it answers |
| --- | --- | --- |
| **Orchestration** | Ray Serve, KServe, Seldon | How many replicas, on which nodes, routed how? |
| **Execution** | **vLLM, NIM, Triton, TensorRT-LLM** | How does one process turn a prompt into tokens? |

This lab chooses an **execution** runtime. KServe is not a competitor to vLLM — KServe *runs* vLLM.

## The Candidates

| Runtime | What it actually is | Licence |
| --- | --- | --- |
| **vLLM** | OSS LLM server. PagedAttention, continuous batching, OpenAI API + Prometheus built in | Apache 2.0 |
| **NVIDIA NIM** | Packaged container around TensorRT-LLM, OpenAI-compatible, NVIDIA-tuned | **NVIDIA AI Enterprise entitlement required** |
| **Triton** | General-purpose inference server. Many backends (ONNX, PyTorch, FIL, Python, TRT-LLM) | BSD-3 |
| **TensorRT-LLM** | Compilation/execution **library**, not a server. No API, no metrics endpoint | Apache 2.0 |

Adjacent, not on this shortlist: **TGI** (close vLLM competitor), **SGLang** (RadixAttention, newer), **LMDeploy**, **Ollama/llama.cpp** (single-user, not multi-tenant), **TorchServe** (no LLM-specific batching).

## Part A — Criteria Before Code (no cluster needed)

Fill this in *before* touching a terminal. A benchmark without criteria is a number in search of a decision.

| # | Criterion | vLLM | NIM | Triton | TRT-LLM |
| --- | --- | --- | --- | --- | --- |
| C1 | Tensor parallel ≤ 2 | | | | |
| C2 | Continuous/dynamic batching | | | | |
| C3 | Token streaming | | | | |
| C4 | OpenAI surface (or adapter cost) | | | | |
| C5 | Prometheus TTFT / queue / KV cache | | | | |
| C6 | Ray Serve integration | | | | |
| C7 | Serves **non-LLM** models too | | | | |
| C8 | Licensing / entitlement | | | | |

Then answer the question most teams skip: **C7 decides whether you end up running one runtime or two.** No LLM-specialised runtime serves classical forecasting models. Triton does — but pays an OpenAI adapter cost on your *primary* workload to serve the secondary one. Two runtimes is a legitimate answer. It just has to be a decision rather than a discovery six months in.

Mark each cell **(r)** read from docs or **(m)** measured. Be honest — most of a runtime evaluation is legitimately read, and pretending otherwise is how paper assessments get quoted as benchmarks.

## Part B — Verify the Claims That Are Checkable Without a GPU

vLLM runs on CPU with a tiny model. Slow, but the *surface* is identical — which is exactly what criteria C3, C4 and C5 are about.

### Check your CPU first

```bash
./scripts/preflight.sh
```

**The prebuilt vLLM CPU images require AVX512.** On a CPU without it the container dies immediately with exit code **132 (SIGILL)** and a log that simply stops after `Automatically detected platform cpu` — no traceback, no error. Verified on an Intel Core Ultra 7 255U (AVX2, no AVX512):

```
State:  Terminated
Reason: Error
Exit Code: 132
```

Modern laptop CPUs — including most Intel Core Ultra and all Apple Silicon — do **not** have AVX512. Server Xeons generally do. If preflight fails you have three options:

1. **Do Part A only.** It needs no cluster, and it is the part that actually makes the decision.
2. Build vLLM from source for your CPU ([docs](https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html)).
3. Run Part B on an AVX512 host — including the GPU nodes you're evaluating anyway.

This is a limitation of the CPU *build*, not of vLLM. GPU images are unaffected.

### Deploy

```bash
kubectl apply -f k8s/01-vllm-cpu.yaml
kubectl rollout status deploy/vllm-cpu --timeout=900s   # image is ~1.3 GB, model load is slow
kubectl port-forward svc/vllm 8000:8000
```

### C4 — Is the OpenAI surface real?

```bash
curl -s localhost:8000/v1/models | jq
curl -s localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"facebook/opt-125m","messages":[{"role":"user","content":"hello"}],"max_tokens":16}' | jq
```

If your gateway already speaks OpenAI, the adapter cost is **zero**. Now compare: Triton's native surface is KServe v2 (`/v2/models/<name>/infer`) — a different request shape, a different streaming mechanism, and a translation layer you own forever.

### C3 — Does streaming work, and is it really incremental?

```bash
curl -N -s localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"facebook/opt-125m","messages":[{"role":"user","content":"count to twenty"}],"max_tokens":64,"stream":true}'
```

Watch for `data: {...}` chunks arriving over time, terminated by `data: [DONE]`. Server-sent events, token by token. A runtime that "supports streaming" by buffering and flushing at the end fails this test.

### C5 — Do the metrics you need actually exist?

This is the criterion that quietly decides whether you can build showback and autoscaling at all.

```bash
curl -s localhost:8000/metrics | grep -E '^# HELP vllm' | head -30
./scripts/check-metrics.sh
```

The three that matter:

| Metric | What it drives |
| --- | --- |
| `vllm:time_to_first_token_seconds` | TTFT SLO — the number users actually feel |
| `vllm:num_requests_waiting` | Queue depth — the correct autoscaling signal |
| `vllm:gpu_cache_usage_perc` | KV cache utilization — how close you are to admission failure |

Scrape them properly:

```bash
kubectl apply -f k8s/02-servicemonitor.yaml   # needs Prometheus Operator
```

**Why this beats CPU utilization for autoscaling:** a GPU pinned at 100% util might be serving 2 requests or 200. Queue depth tells you whether *waiting* is happening. That distinction is the whole reason C5 is on the criteria list.

### C2 — Watch continuous batching happen

```bash
./scripts/load-test.sh 20        # 20 concurrent requests
curl -s localhost:8000/metrics | grep -E 'vllm:num_requests_(running|waiting)'
```

`num_requests_running` climbs above 1 — multiple sequences generating in the *same* forward pass. With static batching, a finished sequence would leave its slot idle until the whole batch drained. With continuous batching a queued request takes that slot at the next token step.

## Part C — GPU Only

Skip if you have no GPU. Nothing above depends on it.

```bash
kubectl apply -f k8s/03-vllm-gpu.yaml     # TP=1, one replica per GPU
kubectl apply -f k8s/04-vllm-gpu-tp2.yaml # TP=2 across two GPUs
./scripts/benchmark.sh
```

### The interconnect trap

Tensor parallelism splits each layer's weights across GPUs, so **every layer ends in an all-reduce** — dozens per forward pass, once per generated token. That collective runs at interconnect speed:

| Interconnect | Bandwidth | Found on |
| --- | --- | --- |
| NVLink 4.0 | ~900 GB/s | H100, H200 |
| PCIe Gen4 x16 | 64 GB/s | **L40S, A10, most PCIe cards** |

**L40S has no NVLink** (NVIDIA spec: "NVLink Support: No") and no MIG. On PCIe-only hardware:

1. **TP=1 is the default** — one replica per GPU gives higher aggregate throughput *and* better fault isolation.
2. **TP=2 is for models that don't fit in one card's memory.** It is capacity, not speed. It usually makes single-request latency worse on PCIe.
3. Check whether peer-to-peer is even enabled — without it, collectives transit host RAM and TP=2 should be abandoned outright:

```bash
nvidia-smi topo -m       # want PIX/PXB, not SYS
```

### Will the model even fit?

```
weights_GB ≈ params_B × bytes_per_param        (bf16 = 2, fp8 = 1)
usable_KV_GB ≈ (gpu_GB × gpu_memory_utilization) − weights_GB
```

Worked example, 2 × L40S (48 GB each, 96 GB total):

| Model | bf16 | fp8 | Fits on 2 × L40S? |
| --- | --- | --- | --- |
| 20B | ~40 GB | ~20 GB | Yes, comfortably at TP=1 |
| 120B | ~240 GB | ~120 GB | **No** — 120 GB > 96 GB before any KV cache |

That's a decision-changing result from arithmetic, before any GPU time is booked. Run the numbers first.

## Break It On Purpose

| Experiment | What you learn |
| --- | --- |
| Set `--max-model-len` very high | Startup fails on KV cache allocation — memory is reserved up front |
| Set `--gpu-memory-utilization 0.95` | Less headroom, more concurrent sequences, closer to OOM |
| Fire 100 concurrent requests | `num_requests_waiting` climbs — see the queue-depth signal move |
| Kill the Pod mid-stream | Client gets a truncated SSE stream. Now you know why replica count matters |
| Request a model that isn't loaded | 404 with an OpenAI-shaped error body — the surface holds even on errors |

## Deliverable

A one-page recommendation containing:

1. The filled criteria table, each cell marked **(r)** or **(m)**
2. One runtime or two — stated as a decision, with the reason
3. The exact version to pin, plus its CUDA/PyTorch pins
4. **What would reverse the decision** — the part everyone omits and everyone later needs

A recommendation without a reversal condition is a preference wearing a lab coat.

## Talking Points

- *"KServe and Ray Serve are orchestration; vLLM and Triton are execution. Choosing between vLLM and KServe is a category error."*
- *"I picked queue depth over GPU utilization for autoscaling — 100% util tells you nothing about whether requests are waiting."*
- *"vLLM's win on PCIe-only hardware comes from PagedAttention and continuous batching — single-GPU memory efficiency — so it loses the least to the absence of NVLink."*
- *"TP=2 without NVLink is a capacity mechanism for oversized models, not a latency optimisation. On PCIe it usually makes latency worse."*
- *"We rejected NIM on entitlement, not on technology. A runtime gated by an unresolved commercial question can't be what every downstream decision is pinned to."*

## References

- [vLLM docs](https://docs.vllm.ai/) · [Prometheus metrics](https://docs.vllm.ai/en/latest/serving/metrics.html)
- [PagedAttention paper](https://arxiv.org/abs/2309.06180)
- [Ray Serve + vLLM](https://docs.ray.io/en/latest/serve/tutorials/vllm-example.html)
- [Triton Inference Server](https://github.com/triton-inference-server/server) · [NVIDIA NIM](https://docs.nvidia.com/nim/)

---

**Verification status:** Part A needs no cluster. Part B manifests were applied on k3s v1.36.4 (Rancher Desktop) on 2026-09-08 — the image pulls and the Deployment schedules, but the container could not start on the test machine because the prebuilt vLLM CPU image needs AVX512 (see the preflight section). The curl/metrics steps in Part B are therefore **written but not executed**; `preflight.sh` was run and correctly detects the limitation. Part C requires a GPU and is **unexecuted**.
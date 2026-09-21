# Serving Runtime Evaluation and Selection (Summary)

**Story:** Evaluate and select the serving runtime
**Status:** Draft for review

## 1. The Goal

We need to pick the core software engine (the "serving runtime") that loads AI models onto our GPUs and processes requests. We are evaluating: **vLLM**, **NVIDIA NIM**, **Triton Inference Server**, and **TensorRT-LLM**.

## 2. Understanding the Stack

It's important to understand where the runtime lives:

- **Kubernetes:** Schedules Pods onto servers.
- **KubeRay / Ray Serve (Orchestration):** Decides *how many* replicas to run, autoscales them, and routes incoming traffic.
- **The Runtime (Execution):** Runs *inside* the Ray Serve pod. This is the engine we are selecting today.

## 3. Our Hardware Reality (The Bottleneck)

Our decision is heavily constrained by our hardware:

- **GPUs:** 3 × NVIDIA L40S (48 GB VRAM each) per server.
- **Interconnect:** PCIe Gen4 only. **There is no NVLink.**

**Why this matters:** Because we lack NVLink, splitting a model across multiple GPUs (Tensor Parallelism = 2) is slow. It forces data through the much slower PCIe bus. Therefore, we prefer running smaller models on a single GPU (TP=1). Massive models (like a 120B parameter model) will not comfortably fit in this environment without heavy quantization.

## 4. Evaluation Criteria

We judged the candidates on:

1. **Hardware Fit:** Works well over PCIe without NVLink.
2. **Performance:** Uses "Continuous Batching" to keep the GPU busy.
3. **User Experience:** Supports token streaming (Server-Sent Events).
4. **Integration:** Natively speaks the OpenAI API format and integrates easily with Ray Serve.
5. **Observability:** Emits Prometheus metrics for queue depth (critical for autoscaling) and Time-to-First-Token (TTFT).
6. **Flexibility:** Can it run both LLMs and standard forecasting models?
7. **Licensing:** Free vs. Paid.

## 5. The Decision: We Need Two Runtimes

No single tool does everything perfectly.

**For LLMs (Text Generation): We select vLLM.**

- **Why:** It is open-source (no licensing fees), natively speaks the OpenAI API, integrates perfectly with Ray Serve, and exposes the exact metrics we need for autoscaling. Crucially, its memory management (PagedAttention) makes it highly efficient on single GPUs, making our lack of NVLink less painful.

**For Non-LLM Workloads (Forecasting): We will use Ray Serve Native or Triton.**

- **Why:** vLLM *only* runs LLMs. Instead of forcing our non-LLM models through a complex Triton setup just to have "one tool," we will deploy them natively via Ray Serve.

## 6. Why the Others Were Rejected (For LLMs)

- **NVIDIA NIM:** Technically excellent, but requires a paid NVIDIA AI Enterprise license, which is currently unresolved.
- **Triton Inference Server:** While it can run anything, it doesn't natively speak the OpenAI API or expose LLM-specific metrics without a heavy translation layer (adapter cost).
- **TensorRT-LLM:** This is just a fast math library, not a web server. We would have to build the API and batching logic ourselves.

---

## Glossary

### Hardware

**NVIDIA L40S**
A data-center GPU designed for inference and graphics workloads. Fits into a standard PCIe slot — no special motherboard required. Each card carries 48 GB of VRAM and ~800 GB/s of internal memory bandwidth. It is the "L" (inference) line, not the "H" line (H100/H200) which is optimised for training. The L40S does not support NVLink.

**VRAM (Video RAM)**
Memory that lives physically on the GPU itself. Completely separate from system RAM. The entire model — weights, activations, and KV cache — must fit in VRAM before a single request can be served. The L40S has 48 GB per card (144 GB across all three), at ~800 GB/s bandwidth. System RAM is larger (≥512 GB) but ~8× slower and unreachable by the GPU directly during inference.

**NVLink**
NVIDIA's proprietary high-speed direct interconnect between GPUs on the same server. Delivers ~900 GB/s GPU-to-GPU bandwidth. Without it, GPUs can only communicate by routing traffic through the CPU over PCIe (~64 GB/s — roughly 14× slower). **The L40S does not support NVLink.** This is the binding hardware constraint for the entire platform: it rules out large models that require fast multi-GPU synchronisation.

**PCIe (Peripheral Component Interconnect Express)**
The slot and bus standard that connects expansion cards (GPUs, SSDs, NICs) to the CPU. Gen4 at x16 lanes provides ~64 GB/s bidirectional bandwidth. On this cluster PCIe is the *only* path for GPU-to-GPU traffic, making it the universal bottleneck for any workload that must split work across GPUs.

**Tensor Parallelism (TP)**
A technique that shards a single model's weight matrices across multiple GPUs so they execute in parallel. TP=2 means one model is split across 2 GPUs; they must synchronise on every transformer layer forward pass. On hardware with NVLink that synchronisation is fast. On this cluster it crosses PCIe, which is slow enough that TP=2 hurts latency compared to running a smaller model entirely on one GPU (TP=1). The registry contract hard-rejects `tensor_parallel_degree > 2` for this reason.

### Serving & Observability

**HPA (Horizontal Pod Autoscaler)**
A built-in Kubernetes controller that watches a metric and adjusts the replica count of a Deployment. Out of the box it only reads CPU and memory — both useless for LLM inference, where a GPU can be at 5% CPU while fully saturated on requests. Wiring in a meaningful signal (queue depth, TTFT) requires a custom Prometheus Adapter. Ray Serve's autoscaler has this built in, which is one reason KubeRay is used instead of relying on HPA alone.

**Queue Depth**
The number of incoming requests waiting to be picked up by a model replica. When queue depth climbs, it means existing replicas are saturated and new ones should be started. This is the primary autoscaling signal for inference: more meaningful than CPU%, more actionable than memory%. vLLM exposes it as a native Prometheus metric; Ray Serve reads it to decide when to scale out.

**TTFT (Time to First Token)**
The elapsed time from when a request arrives until the first token streams back to the client. A user can tolerate a slow stream but not a long blank pause before anything appears, so TTFT is the key perceived-latency metric for LLM serving. It is LLM-specific — no generic Kubernetes or web-serving tool understands it natively. It is listed as a required Prometheus metric in the INF-01 acceptance criteria (criterion C5).

**KV Cache (Key-Value Cache)**
During inference the model computes attention over every prior token in the context window. The intermediate results — keys and values from each attention layer — are stored in VRAM so they are not recomputed on every new token. This cache is what PagedAttention (vLLM's core memory management feature) organises efficiently. When the KV cache fills, new requests must wait or be rejected. KV cache utilisation % is therefore a hard capacity signal and a required metric in C5 — more directly tied to accepting new requests than GPU compute utilisation.

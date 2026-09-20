# Serving Runtime Evaluation and Selection (Summary)

**Story:** Evaluate and select the serving runtime
**Status:** Draft for review

## 1. The Goal
We need to pick the core software engine (the "serving runtime") that loads AI models onto our GPUs and processes requests. We are evaluating: **vLLM**, **NVIDIA NIM**, **Triton Inference Server**, and **TensorRT-LLM**.

## 2. Understanding the Stack
It's important to understand where the runtime lives:
*   **Kubernetes:** Schedules Pods onto servers.
*   **KubeRay / Ray Serve (Orchestration):** Decides *how many* replicas to run, autoscales them, and routes incoming traffic.
*   **The Runtime (Execution):** Runs *inside* the Ray Serve pod. This is the engine we are selecting today.

## 3. Our Hardware Reality (The Bottleneck)
Our decision is heavily constrained by our hardware:
*   **GPUs:** 3 × NVIDIA L40S (48 GB VRAM each) per server.
*   **Interconnect:** PCIe Gen4 only. **There is no NVLink.** 

**Why this matters:** Because we lack NVLink, splitting a model across multiple GPUs (Tensor Parallelism = 2) is slow. It forces data through the much slower PCIe bus. Therefore, we prefer running smaller models on a single GPU (TP=1). Massive models (like a 120B parameter model) will not comfortably fit in this environment without heavy quantization.

## 4. Evaluation Criteria
We judged the candidates on:
1.  **Hardware Fit:** Works well over PCIe without NVLink.
2.  **Performance:** Uses "Continuous Batching" to keep the GPU busy.
3.  **User Experience:** Supports token streaming (Server-Sent Events).
4.  **Integration:** Natively speaks the OpenAI API format and integrates easily with Ray Serve.
5.  **Observability:** Emits Prometheus metrics for queue depth (critical for autoscaling) and Time-to-First-Token (TTFT).
6.  **Flexibility:** Can it run both LLMs and standard forecasting models?
7.  **Licensing:** Free vs. Paid.

## 5. The Decision: We Need Two Runtimes

No single tool does everything perfectly. 

**For LLMs (Text Generation): We select vLLM.**
*   **Why:** It is open-source (no licensing fees), natively speaks the OpenAI API, integrates perfectly with Ray Serve, and exposes the exact metrics we need for autoscaling. Crucially, its memory management (PagedAttention) makes it highly efficient on single GPUs, making our lack of NVLink less painful.

**For Non-LLM Workloads (Forecasting): We will use Ray Serve Native or Triton.**
*   **Why:** vLLM *only* runs LLMs. Instead of forcing our non-LLM models through a complex Triton setup just to have "one tool," we will deploy them natively via Ray Serve.

## 6. Why the Others Were Rejected (For LLMs)
*   **NVIDIA NIM:** Technically excellent, but requires a paid NVIDIA AI Enterprise license, which is currently unresolved. 
*   **Triton Inference Server:** While it can run anything, it doesn't natively speak the OpenAI API or expose LLM-specific metrics without a heavy translation layer (adapter cost).
*   **TensorRT-LLM:** This is just a fast math library, not a web server. We would have to build the API and batching logic ourselves.

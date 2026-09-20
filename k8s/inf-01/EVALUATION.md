# INF-01 Runtime Evaluation Matrix & Guide

This document captures the evaluation of our four candidate runtimes based on the criteria in the INF-01 story. It serves as both an educational guide for the team and the final evaluation matrix.

---

## 1. The Runtimes: What are they?
AI models are giant mathematical files (weights). They cannot run themselves; they need an engine to load them into GPU memory, manage incoming requests, and compute the math. That engine is the **serving runtime**.

*   **vLLM:** The open-source standard (Apache 2.0). It pioneered "PagedAttention" (highly efficient memory management to serve more users on one GPU). It is built *specifically* for LLMs, natively speaks the OpenAI API, and exposes Prometheus metrics out of the box. **Catch:** It only runs LLMs.
*   **TensorRT-LLM (TRT-LLM):** NVIDIA's core optimization *library*. It is **not a server**. It is a compiler that makes LLM math run blindingly fast on NVIDIA GPUs. Because it has no HTTP API or metrics, you cannot deploy it on its own. It is typically wrapped inside Triton.
*   **Triton Inference Server:** NVIDIA's general-purpose open-source server. It can serve *anything*—classic machine learning (like forecasting models), Python scripts, and LLMs. **Catch:** Its native API is not OpenAI-compatible by default, requiring a translation adapter, and it is complex to configure.
*   **NVIDIA NIM:** NVIDIA's enterprise "easy button." It is a pre-packaged Docker container that bundles Triton, TRT-LLM, and an OpenAI API wrapper together, highly tuned for specific GPUs. **Catch:** It requires a paid NVIDIA AI Enterprise license (entitlement).

## 2. How KubeRay Helps (Orchestration vs. Execution)
KubeRay and runtimes like vLLM are not competitors; they operate at different layers:
*   **Kubernetes** schedules Pods on nodes.
*   **KubeRay (Ray Serve)** is the **Orchestrator**. It watches queue depth metrics, decides *how many* Pods are needed, spins them up, and routes traffic to the least busy replica.
*   **vLLM / Triton / NIM** is the **Execution layer**. It lives *inside* the KubeRay Pod, loads the weights, and actually generates the tokens. 

KubeRay doesn't care which execution runtime you pick; it handles the scaling and routing for it.

---

## 3. The Acceptance Criteria, Translated

To ensure the platform team isn't configuring four different systems, we must pick *one* standard runtime (or make a deliberate decision to support two). 

1. **Tensor-parallel ≤ 2:** If a model is too big for one GPU's memory, can the runtime split the math across 2 GPUs? 
2. **Continuous/Dynamic batching:** Does it intelligently group incoming user prompts at the token level so the GPU is never sitting idle? (Crucial for high throughput).
3. **Token streaming:** Can it stream responses back word-by-word (like ChatGPT) using Server-Sent Events (SSE)?
4. **OpenAI-compatible:** Can existing apps talk to it via `/v1/chat/completions`? If not, we pay an engineering tax to build an adapter.
5. **Prometheus metrics:** Does it natively track Time To First Token (TTFT), queue depth, and GPU memory? **Queue depth is how you autoscale.** Scaling on 100% GPU utilization fails because a GPU at 100% could be serving 2 users or 200. You scale when the *queue* grows.
6. **Ray Serve integration:** Can KubeRay easily deploy and manage this runtime?
7. **Non-LLM support:** Will this runtime also serve our classical forecasting models? If we pick vLLM (LLM-only), we explicitly accept that our platform will need *two* runtimes (e.g., vLLM for text, Triton for forecasting). 
8. **Licensing:** Does it require a commercial agreement (NIM) or is it free (vLLM/Triton)?

---

## 4. Evaluation Matrix

**Definitions:**
- **(r)** = Read from documentation (not yet tested on hardware)
- **(m)** = Measured on actual hardware / cluster via POCs

| # | Criterion | vLLM | NVIDIA NIM | Triton Inference Server | TensorRT-LLM |
|---|---|---|---|---|---|
| C1 | Tensor-parallel (TP) ≤ 2 | | | | |
| C2 | Continuous/Dynamic batching | | | | |
| C3 | Token streaming | | | | |
| C4 | OpenAI surface (or adapter cost) | | | | |
| C5 | Prometheus TTFT / queue / KV cache metrics | | | | |
| C6 | Ray Serve integration | | | | |
| C7 | Serves **non-LLM** models too | | | | |
| C8 | Licensing / Entitlement required | | | | |

## 5. Final Recommendation
*(To be filled out after the matrix is completed and team review)*
- **Chosen Runtime(s):**
- **Reasoning:**
- **Version to Pin:**
- **Reversal Condition (What would make us change our minds?):**

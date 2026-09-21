# INF-01 Runtime Evaluation Matrix

This document captures the hands-on evaluation of our four candidate runtimes based on the criteria in the INF-01 story.

*(For a high-level summary of the architectural context, hardware constraints, and final decision, see `Serving_Runtime_Evaluation_and_Selection.md`.)*

## 1. How KubeRay Fits In

KubeRay acts as our **Orchestrator**. It watches queue depth metrics and spins up/routes traffic to the execution runtime pods. The runtimes evaluated below act as the **Execution layer** living *inside* those KubeRay pods.

## 2. Evaluation Matrix

Our specific hardware constraint (3 × L40S, PCIe Gen4, no NVLink) means that single-node efficiency (TP=1) and memory management are critical. We evaluated the candidates against these requirements:

**Definitions:**

- **(r)** = Read from documentation (not yet tested on hardware)
- **(m)** = Measured on actual hardware / cluster via POCs

| # | Criterion | vLLM | NVIDIA NIM | Triton Inference Server | TensorRT-LLM |
| --- | --- | --- | --- | --- | --- |
| C1 | Tensor-parallel (TP) ≤ 2 | | | | |
| C2 | Continuous/Dynamic batching | | | | |
| C3 | Token streaming | | | | |
| C4 | OpenAI surface (or adapter cost) | | | | |
| C5 | Prometheus TTFT / queue / KV cache metrics | | | | |
| C6 | Ray Serve integration | | | | |
| C7 | Serves **non-LLM** models too | | | | |
| C8 | Licensing / Entitlement required | | | | |

## 3. POC Usage

You can test the API surfaces locally using the CPU-only POC deployments provided in this directory:

1. `kubectl apply -f 01-vllm-cpu-poc.yaml`
2. `kubectl port-forward svc/vllm-poc-svc 8000:8000`
3. Run `scripts/test-openai-surface.sh localhost:8000` to verify criteria C3 and C4.

## 4. Final Recommendation

To be filled out after the matrix is completed and team review:

- **Chosen Runtime(s):**
- **Reasoning:**
- **Version to Pin:**
- **Reversal Condition (What would make us change our minds?):**

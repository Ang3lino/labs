# EPIC-05: Inference Serving

## Story: INF-01 Evaluate and select the serving runtime

**As the** platform team,  
**I want** one runtime chosen on evidence across vLLM, NVIDIA NIM, Triton Inference Server, and TensorRT-LLM,  
**So that** every downstream decision—engine flags, metric names, batching, packaging—is made once against a known target.

### Acceptance Criteria

- **Comprehensive Assessment:** All four candidates must be assessed against a written criteria set covering, at minimum:
  - Tensor-parallel support (maximum degree of 2)
  - Continuous or dynamic batching
  - Token streaming
  - OpenAI-compatible request surface (or the adapter engineering cost of providing one)
  - Native Prometheus metrics (including TTFT, queue depth, and KV cache utilization)
  - Ray Serve integration
  - Support for the non-LLM forecasting class (which needs no tensor parallelism at all)
  - Licensing and entitlement requirements (specifically addressing NIM's NVIDIA entitlement question)
- **Workload Coverage:** Explicitly record whether each candidate serves both workload classes, or whether the platform ends up running two runtimes. (Running two is an acceptable outcome, but it must be a conscious decision rather than a later discovery).
- **Hardware Constraints:** The assessment must be performed using the two-GPU ceiling as a fixed constraint, not as a variable.
- **Security & Compliance:** The approved-software status of each candidate and its dependencies must be checked *before* the recommendation is made, not after.
- **Final Deliverable:** A written recommendation detailing the reason for the choice, the exact version proposed for pinning, and the specific conditions that would reverse the decision.
- **Justification:** Existing documents assume vLLM; if the recommendation is vLLM, the reasoning must still be explicitly written down rather than inherited.

### Metadata

- **Depends on:** Nothing (no other story)
- **Proposed Owner:** Platform Team

> **Note:** Evaluating four runtimes properly against unbuilt hardware is not possible before mid-October. The realistic shape of this task is a paper assessment against the criteria above, followed by hands-on time with the leading two candidates once GPU One is reachable. The final evaluation must clearly state which parts were *measured* vs. which were *read*.

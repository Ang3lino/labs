# Registry Contract Enforcement (PoC)

**Epic:** EPIC-05 Inference Serving  
**Story:** INF-05 Consume the registry contract, and refuse artifacts that do not carry it

## 1. Overview
This Proof of Concept (PoC) demonstrates the deployment gating mechanism between the Model Registry (MLflow) and the Serving Layer (KubeRay). 

To achieve a fully automated "promotion becomes a deployment" workflow, we enforce a strict **Metadata Contract**. If a Data Scientist promotes a model that is missing critical operational parameters, the deployment is automatically rejected before it ever touches the Kubernetes cluster.

## 2. The Contract Fields
Every artifact promoted to Production must carry the following 11 fields as tags in MLflow. The serving layer reads these tags to configure the RayService manifest.

1. `runtime`: The execution engine (e.g., `vllm`).
2. `runtime_version`: The specific container version (e.g., `0.5.0`).
3. `quantization_precision`: How the weights are formatted (e.g., `bf16`, `fp8`, `awq`).
4. `tensor_parallel_degree`: The number of GPUs to split the model across.
5. `accelerator`: The hardware target (e.g., `L40S`).
6. `max_context`: The maximum context window to allocate KV cache for.
7. `evaluated_concurrency`: The load target the model was tested against.
8. `preprocessing_tokenizer`: The HuggingFace tokenizer path.
9. `resource_profile`: The T-shirt size for CPU/RAM sidecar allocation.
10. `artifact_digest`: The exact immutable hash of the model weights.
11. `owning_team`: The billing/attribution identifier.

## 3. Enforcement Rules
The deployment webhook (`contract_enforcer.py`) applies the following rules:

*   **Strict Presence:** Missing any of the 11 fields results in an immediate failure naming the exact missing field. We do *not* guess or fall back to defaults.
*   **Promotion Gating:** Artifacts with a state other than `Production` (or `Promoted`) are rejected.
*   **Hardware Ceiling:** Tensor Parallelism (`tensor_parallel_degree`) above `2` is strictly rejected. This is tied to our L40S PCIe constraints, preventing developers from attempting to deploy 120B+ models that require NVLink.
*   **Metric Attribution:** Upon successful validation, the `owning_team` field is extracted and injected as a label into the KubeRay manifest. This ensures the downstream Grafana consumption dashboard correctly attributes the GPU costs.

## 4. Running the PoC
A Python-based simulation of the deployment webhook is provided in this directory.

```bash
# Run the deployment enforcer
python3 contract_enforcer.py
```

### Expected Output
The script reads `test-payloads.json` and evaluates four scenarios:
1.  **llama-3-8b-instruct:** Passes all checks. Shows how `owning_team` is propagated.
2.  **gemma-2b:** Fails because it is missing the `runtime_version` (and other) fields.
3.  **mixtral-8x7b:** Fails because its promotion state is `Staging`, not `Production`.
4.  **llama-120b:** Fails because it requests a tensor-parallel degree of 4, exceeding the fleet ceiling of 2.

## 5. Cross-Epic Alignment
Any gap between the 11 fields required above and the fields MLflow natively captures today must be documented as a checklist and handed to the Training Pipeline Epic owner. The Training Pipeline is responsible for ensuring these tags are attached during the CI/CD pipeline runs.

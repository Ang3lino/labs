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

- **Strict Presence:** Missing any of the 11 fields results in an immediate failure naming the exact missing field. We do *not* guess or fall back to defaults.
- **Promotion Gating:** Artifacts with a state other than `Production` (or `Promoted`) are rejected.
- **Hardware Ceiling:** Tensor Parallelism (`tensor_parallel_degree`) above `2` is strictly rejected. This is tied to our L40S PCIe constraints, preventing developers from attempting to deploy 120B+ models that require NVLink.
- **Metric Attribution:** Upon successful validation, the `owning_team` field is extracted and injected as a label into the KubeRay manifest. This ensures the downstream Grafana consumption dashboard correctly attributes the GPU costs.

## 4. Running the PoC

### Prerequisites

```bash
cd inf-05
pip install -r requirements.txt
```

### Run the tests

The test suite covers every acceptance criterion. No MLflow server required —
`MLFLOW_MOCK=1` makes the adapter read `test-payloads.json` instead.

```bash
cd inf-05
python3 -m pytest test_contract_enforcer.py -v
```

### Start the webhook

```bash
cd inf-05
MLFLOW_MOCK=1 uvicorn src.contract_enforcer:app --host 0.0.0.0 --port 8080
```

### Exercise the four scenarios

```bash
# 1. Accepted — all fields present, owning_team propagated to manifest labels
curl -s http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"model_name":"llama-3-8b-instruct","model_version":"1"}' | python3 -m json.tool

# 2. Rejected — missing runtime_version (and other fields)
curl -s http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"model_name":"gemma-2b","model_version":"1"}' | python3 -m json.tool

# 3. Rejected — promotion state is Staging, not Production/Promoted
curl -s http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"model_name":"mixtral-8x7b","model_version":"1"}' | python3 -m json.tool

# 4. Rejected — tensor_parallel_degree=4 exceeds fleet ceiling of 2
curl -s http://localhost:8080/validate \
  -H "Content-Type: application/json" \
  -d '{"model_name":"llama-120b","model_version":"1"}' | python3 -m json.tool
```

### Connect to a real MLflow server

Unset `MLFLOW_MOCK` and point at your tracking server:

```bash
MLFLOW_TRACKING_URI=http://mlflow.internal:5000 \
  uvicorn src.contract_enforcer:app --host 0.0.0.0 --port 8080
```

The webhook will call `MlflowClient().get_model_version(name, version)` and
read `current_stage` and `tags` directly from the registry.

## 5. Cross-Epic Alignment

See `cross_epic_gaps.md` for the full documented gap list. 10 of the 11
contract fields require explicit tagging by the Training Pipeline CI/CD —
MLflow does not capture them natively. This list must be handed to the
Training Pipeline epic owner before production deployment is possible.

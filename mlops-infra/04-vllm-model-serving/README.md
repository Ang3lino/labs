# Lab 04 — LLM Serving with vLLM + KServe

## Summary

Deploy an open-source LLM as an OpenAI-compatible API on Kubernetes using vLLM for high-throughput inference and KServe for production model serving with auto-scaling, canary rollouts, and request batching.

## Problem It Solves

You have a 70B parameter model. Without a proper serving stack:
- Loading the model takes 5 minutes → first request waits 5 min
- Sequential processing → 1 request at a time, 50 users waiting
- No batching → GPU utilization at 15% while processing single requests
- No auto-scaling → 3am = paying for idle GPUs, 3pm = overloaded
- New model version → downtime during swap

vLLM solves the inference engine problem (fast, batched, paged attention). KServe solves the platform problem (scaling, routing, versioning, health checks).

## How It Works Under the Hood

### vLLM Engine

```
┌─────────────────────────────────────────────────────────────────┐
│ vLLM Server                                                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Continuous Batching Engine                                  │ │
│  │                                                            │ │
│  │  Request Queue:  [req1, req2, req3, req4, req5]            │ │
│  │       ↓                                                    │ │
│  │  Scheduler: "req1 is at token 50, req2 at token 3,        │ │
│  │             req3 just arrived — batch all together"         │ │
│  │       ↓                                                    │ │
│  │  ┌──────────────────────────────────────┐                  │ │
│  │  │ PagedAttention (KV-Cache)            │                  │ │
│  │  │                                      │                  │ │
│  │  │ GPU Memory split into "pages"        │                  │ │
│  │  │ Each request gets pages on demand    │                  │ │
│  │  │ No pre-allocation waste              │                  │ │
│  │  │ Pages freed when request completes   │                  │ │
│  │  └──────────────────────────────────────┘                  │ │
│  │       ↓                                                    │ │
│  │  Output: stream tokens back per-request                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  OpenAI-compatible API:                                          │
│    POST /v1/chat/completions                                     │
│    POST /v1/completions                                          │
│    GET  /v1/models                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Why vLLM is faster than naive serving:**

| Technique | What it does | Speedup |
|---|---|---|
| **PagedAttention** | KV-cache stored in non-contiguous pages (like OS virtual memory) | 2-4x memory efficiency |
| **Continuous batching** | New requests join mid-batch, no waiting for batch to finish | 10-20x throughput vs sequential |
| **Tensor parallelism** | Split model across multiple GPUs | Linear scaling with GPU count |
| **Prefix caching** | Shared system prompts cached across requests | Saves recomputation |
| **Speculative decoding** | Draft model proposes, main model verifies in parallel | 2x latency reduction |

### KServe (Model Serving Platform)

```
┌─────────────────────────────────────────────────────────────────┐
│ KServe InferenceService                                          │
│                                                                  │
│  External Traffic                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────┐     ┌─────────────────────────────────┐          │
│  │ Ingress  │────>│ Knative / Istio (routing)       │          │
│  └──────────┘     └────────────┬────────────────────┘          │
│                                 │                                │
│                    ┌────────────┼────────────────┐              │
│                    ▼            ▼                ▼              │
│              ┌──────────┐ ┌──────────┐    ┌──────────┐         │
│              │ Predictor│ │ Predictor│    │ Predictor│         │
│              │ (vLLM)   │ │ (vLLM)   │    │ (vLLM)   │         │
│              │ replica 1│ │ replica 2│    │ replica 3│         │
│              │ GPU: 1   │ │ GPU: 1   │    │ GPU: 1   │         │
│              └──────────┘ └──────────┘    └──────────┘         │
│                                                                  │
│  Auto-scaling: queue depth > 5 → add replica                    │
│  Scale to zero: no traffic for 5min → terminate all             │
│  Canary: 90% → v1, 10% → v2 (new model version)               │
└─────────────────────────────────────────────────────────────────┘
```

**KServe adds on top of raw vLLM:**
- Auto-scaling (including scale-to-zero)
- Canary/blue-green rollouts for model versions
- Request/response logging
- Transformer (pre/post-processing sidecar)
- Multi-model serving
- Standard inference protocol (V2)

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **vLLM** | LLM inference (chat, completion). Highest throughput open-source engine. | Non-LLM models (use Triton), tiny models (overkill) |
| **TGI (Text Generation Inference)** | HuggingFace ecosystem, slightly simpler setup | When you need max throughput (vLLM is faster) |
| **Triton Inference Server** | Multi-framework (PyTorch, TensorFlow, ONNX), non-LLM models | Pure LLM serving (vLLM is better for this) |
| **Ollama** | Local dev, single-user, dead simple | Production multi-user serving (no batching, no scaling) |
| **KServe** | K8s-native model serving with auto-scaling, canary, multi-model | Non-K8s environments, simple single-model deploys |
| **Ray Serve** | Python-native serving, complex preprocessing pipelines | When you want K8s-native operations (KServe is better) |
| **NVIDIA NIM** | Pre-optimized containers, enterprise support | Open-source-only, need full control |
| **SageMaker Endpoints** | AWS-managed, zero infra | On-prem, multi-cloud |

**Decision rule for LLM serving**: vLLM (engine) + KServe (platform) on K8s. This is what the HPE project uses.

## Industry Scenarios

| Company / Pattern | Stack |
|---|---|
| **HPE AI Platform** (your project) | vLLM/NIM/Triton on K8s with KServe, OpenAI-compatible API gateway |
| **Anyscale (Ray team)** | vLLM on Ray Serve |
| **Cloudflare Workers AI** | Modified vLLM on custom infra |
| **Azure OpenAI Service** | Triton + custom routing (not open-source) |
| **Any startup serving LLMs** | vLLM on K8s (often via RunPod, Modal, or self-hosted) |
| **Enterprise on-prem** | vLLM + KServe + GPU Operator = the standard stack |

## Key Terms

- `vLLM` — high-throughput LLM inference engine
- `PagedAttention` — virtual memory for KV-cache
- `Continuous batching` — dynamic batching of in-flight requests
- `Tensor parallelism` — split model across GPUs
- `KServe InferenceService` — K8s CRD for model serving
- `Predictor` — the actual model container
- `Transformer` — pre/post-processing sidecar
- `Canary rollout` — route % of traffic to new model version
- `Scale to zero` — terminate pods when no traffic
- `OpenAI-compatible API` — `/v1/chat/completions` endpoint
- `KV-cache` — stored attention keys/values for generation
- `tokens/sec` — throughput metric
- `TTFT (Time To First Token)` — latency metric

## Interview Talking Points

"I serve LLMs on K8s using vLLM for the inference engine — it gives us 10-20x throughput over naive serving through continuous batching and PagedAttention. KServe handles the platform layer: auto-scaling based on queue depth, canary rollouts when we swap model versions, and scale-to-zero for cost savings. The API is OpenAI-compatible so consuming applications don't care whether they're hitting our on-prem vLLM or a cloud API — same interface. I've deployed models up to 70B parameters using tensor parallelism across 4 GPUs."

## Exercises

### Exercise 1: Run vLLM locally (Docker)

```bash
# Serve a small model (fits on 1 GPU or even CPU for testing)
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model microsoft/Phi-3-mini-4k-instruct \
  --max-model-len 4096

# Test with curl (OpenAI-compatible!)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "microsoft/Phi-3-mini-4k-instruct",
    "messages": [{"role": "user", "content": "What is Kubernetes?"}],
    "max_tokens": 100
  }'

# List available models
curl http://localhost:8000/v1/models
```

### Exercise 2: Deploy vLLM on K8s (raw Deployment)

```yaml
# vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-phi3
  namespace: ml-serving
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-phi3
  template:
    metadata:
      labels:
        app: vllm-phi3
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - "--model"
        - "microsoft/Phi-3-mini-4k-instruct"
        - "--max-model-len"
        - "4096"
        - "--gpu-memory-utilization"
        - "0.9"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "16Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "12Gi"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 10
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      volumes:
      - name: model-cache
        persistentVolumeClaim:
          claimName: hf-cache
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-phi3
  namespace: ml-serving
spec:
  selector:
    app: vllm-phi3
  ports:
  - port: 8000
    targetPort: 8000
```

```bash
kubectl apply -f vllm-deployment.yaml
kubectl port-forward svc/vllm-phi3 8000:8000 -n ml-serving
curl localhost:8000/v1/models
```

### Exercise 3: Deploy with KServe (production)

```yaml
# kserve-vllm.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: phi3-llm
  namespace: ml-serving
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 5
    scaleTarget: 5          # scale up when queue > 5 requests
    scaleMetric: concurrency
    containers:
    - name: kserve-container
      image: vllm/vllm-openai:latest
      args:
      - "--model"
      - "microsoft/Phi-3-mini-4k-instruct"
      - "--max-model-len"
      - "4096"
      ports:
      - containerPort: 8000
        protocol: TCP
      resources:
        limits:
          nvidia.com/gpu: 1
          memory: "16Gi"
```

```bash
# Install KServe (one-time)
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.13.0/kserve.yaml

kubectl apply -f kserve-vllm.yaml
kubectl get inferenceservice phi3-llm -n ml-serving

# Get the URL
SERVICE_URL=$(kubectl get inferenceservice phi3-llm -n ml-serving -o jsonpath='{.status.url}')
curl $SERVICE_URL/v1/chat/completions -d '{"model":"phi3","messages":[{"role":"user","content":"Hello"}]}'
```

### Exercise 4: Canary rollout (swap model versions)

```yaml
# Update InferenceService with canary traffic split
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: phi3-llm
  annotations:
    serving.kserve.io/canaryTrafficPercent: "10"
spec:
  predictor:
    canaryContainers:
    - name: kserve-container
      image: vllm/vllm-openai:latest
      args: ["--model", "microsoft/Phi-3.5-mini-instruct"]  # new version
      resources:
        limits:
          nvidia.com/gpu: 1
```

90% traffic → Phi-3, 10% → Phi-3.5. Monitor metrics, then promote.

### Exercise 5: Load test and observe auto-scaling

```bash
# Install hey (HTTP load tester)
go install github.com/rakyll/hey@latest

# Blast 50 concurrent requests
hey -n 200 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"phi3","messages":[{"role":"user","content":"Count to 10"}],"max_tokens":50}' \
  http://localhost:8000/v1/chat/completions

# Watch replicas scale up
kubectl get pods -n ml-serving -w
```

### Exercise 6: Tensor parallelism (multi-GPU)

```yaml
# For larger models (70B needs 4x A100)
args:
- "--model"
- "meta-llama/Meta-Llama-3-70B-Instruct"
- "--tensor-parallel-size"
- "4"                    # split across 4 GPUs
- "--max-model-len"
- "8192"
resources:
  limits:
    nvidia.com/gpu: 4    # request 4 GPUs
```

## References

- [vLLM documentation](https://docs.vllm.ai/)
- [KServe documentation](https://kserve.github.io/website/)
- [PagedAttention paper](https://arxiv.org/abs/2309.06180)
- [vLLM blog — continuous batching](https://blog.vllm.ai/2023/06/20/vllm.html)
- [KServe + vLLM integration guide](https://kserve.github.io/website/latest/modelserving/v1beta1/llm/vllm/)
- *Designing Machine Learning Systems* Ch.7 (Model Deployment)

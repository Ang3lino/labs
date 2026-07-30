# Lab 04 — Deploy & Serve

This lab covers MLA-C01 Domain 3 (Deployment & Orchestration, 22%) by serving a trained fraud model using both managed SageMaker endpoints and container/Kubernetes patterns.

## Theory

### SageMaker endpoint types: when to use each

- **Real-time endpoint**: low-latency, always-on inference for interactive APIs and user-facing requests.
- **Serverless inference**: bursty or low-throughput workloads where paying only per request is better than running idle instances.
- **Async endpoint**: payloads or model runtimes too large/slow for strict online latency; request is queued and processed asynchronously.
- **Batch transform**: offline bulk scoring at scale where latency per record is not critical.

### BYOC pattern and Amazon ECR

Bring Your Own Container (BYOC) lets you package custom inference logic, dependencies, and model loading behavior in Docker. The image is pushed to **Amazon ECR**, then used by SageMaker, EKS, or ECS. This is the main pattern when built-in framework containers are not enough.

### EKS for model serving

**Amazon EKS** is useful when you need Kubernetes-native controls: advanced networking/policy, sidecars, custom autoscaling, and unified platform operations across many microservices.

### ECS Fargate vs EKS vs Lambda tradeoffs

- **ECS Fargate**: simpler than EKS, no cluster node management, good for container-first teams with moderate orchestration needs.
- **EKS**: most flexible/orchestrator-rich, best for complex multi-service platform patterns, but highest operational complexity.
- **Lambda inference**: fastest path for tiny models and event-driven workloads, but package/runtime constraints and cold starts limit larger ML serving.

### Auto-scaling policies

- **Target tracking**: keep a metric near a target value (for example, InvocationsPerInstance).
- **Step scaling**: add/remove capacity in tiers when thresholds are crossed.
- **Scheduled scaling**: pre-scale for known traffic windows.

### Multi-model endpoints

Multi-model endpoints allow many models behind one endpoint, loading models on demand. Useful for large model catalogs with sparse traffic per model.

### SageMaker Neo for edge

**SageMaker Neo** compiles models for target edge/device hardware to reduce latency and footprint.

### Compute instance selection for inference

- **ml.m5**: balanced general-purpose CPU for many standard tabular/text models.
- **ml.c5**: compute-optimized CPU when CPU throughput is the bottleneck.
- **ml.p3**: GPU instances for deep learning models requiring GPU acceleration.
- **ml.inf**: inference-optimized instances (Inferentia) for cost/performance efficiency at scale.

## Key Terms

- SageMaker real-time endpoint
- SageMaker serverless inference
- SageMaker async endpoint
- SageMaker batch transform
- Bring Your Own Container (BYOC)
- Amazon ECR
- Amazon EKS
- Amazon ECS Fargate
- AWS Lambda inference
- Kubernetes Deployment
- Kubernetes Service
- Horizontal Pod Autoscaler (HPA)
- SageMaker endpoint auto-scaling
- SageMaker Neo
- multi-model endpoint
- inference pipeline
- shadow variant
- production variant
- EKS vs ECS vs Lambda serving tradeoffs

## Interview Talking Points

"I deployed ML models across SageMaker endpoints and Kubernetes. I built a custom Docker container for a PyTorch model, pushed it to ECR, deployed to both a SageMaker real-time endpoint with auto-scaling and to EKS with HPA. I compared latency, cost, and operational overhead between SageMaker, EKS, ECS Fargate, and Lambda."

## Exam Tips

- Domain 3 is 22% of MLA-C01.
- Know the 4 endpoint types and exactly when to choose each.
- Know BYOC Docker container structure for inference.
- Know auto-scaling metrics: **InvocationsPerInstance**, **CPUUtilization**, **ModelLatency**.
- Know EKS vs ECS vs Lambda serving tradeoffs.

## References

- *Designing ML Systems* (Chip Huyen), Chapter 7
- AWS SageMaker BYOC documentation
- *Kubernetes in Action* (Marko Lukša)
- AWS EKS Workshop: https://www.eksworkshop.com/

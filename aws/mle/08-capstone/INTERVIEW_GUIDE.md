# Lab 08 Capstone — Interview Guide

## 5-Minute Project Walkthrough Script

"This capstone is my end-to-end fraud detection ML platform on AWS, and it intentionally consolidates every major pattern from Labs 01-07.

I start with data in S3 and run ETL with Glue to standardize records and produce model-ready features. Those features are ingested into SageMaker Feature Store so I can support both offline training datasets and online inference consistency.

For model development, I use SageMaker PyTorch script mode. I chose PyTorch because it gives me direct control over training logic while staying within managed SageMaker infrastructure. I run Bayesian hyperparameter tuning with AMT, then register the best model in Model Registry so model promotion is governed and auditable.

For serving, I deploy to a SageMaker real-time endpoint and attach target tracking auto-scaling on InvocationsPerInstance=70, so capacity follows request volume automatically. I keep an optional EKS path to show how the same model can fit a Kubernetes platform strategy when needed.

For reliability, I configure Model Monitor for data quality checks and Clarify for explainability and drift visibility. CloudWatch dashboards and alarms give me operational visibility across latency, errors, and traffic.

For MLOps automation, EventBridge listens for new raw data in S3 and triggers retraining via a SageMaker Pipeline. The pipeline is process → train → evaluate → condition gate → register, so model quality gates are built-in.

Security and cost are first-class: IAM least privilege, KMS encryption, VPC endpoints, plus cost controls like Spot for training and rightsizing recommendations for inference. So this is not just model code — it is a production ML operating system." 

## Common Follow-Up Questions and Answers

### Why PyTorch over TensorFlow?

- Strong market demand and broad practitioner familiarity.
- SageMaker script mode support is mature and practical for production workflows.
- Clean research-to-production bridge: rapid experimentation with straightforward deployment integration.

### Why SageMaker over self-hosted?

- Managed infrastructure reduces undifferentiated ops overhead.
- Built-in HPO, monitoring, and model registry remove many custom platform tasks.
- Better cost controls with managed tooling (auto-scaling, spot, usage observability).

### How do you handle drift?

- Model Monitor detects data quality and model quality drift.
- CloudWatch alarms surface threshold breaches.
- EventBridge triggers retraining pipeline when new data arrives or drift thresholds are exceeded.

### What's your deployment strategy?

- Blue/green as the default safety pattern for production release.
- Canary traffic shifting for incremental risk reduction before full rollout.
- Endpoint auto-scaling driven by InvocationsPerInstance keeps latency/cost balanced.

### How do you manage costs?

- Spot Instances for fault-tolerant training workloads.
- Inference Recommender for rightsizing endpoint instance types.
- Savings Plans for predictable long-running usage.
- Resource tagging and periodic cost reports for ownership and cleanup.

### What would you do differently?

- Add a formal A/B testing framework for statistically rigorous online comparisons.
- Expand feature store versioning semantics beyond dataset version metadata.
- Increase monitoring granularity for business KPI-linked alerting.

## System Design Diagram Explanation

When whiteboarding this system:

1. Start with the **left-to-right flow**: S3 raw data → Glue ETL → Feature Store.
2. Move to **model lifecycle**: PyTorch training + AMT → Model Registry.
3. Explain **serving path**: SageMaker endpoint primary, EKS optional strategy branch.
4. Layer **observability** on top: Model Monitor, Clarify, CloudWatch metrics/alarms.
5. Close with **feedback loop**: EventBridge trigger → SageMaker Pipeline retraining.
6. Add **cross-cutting concerns** around the diagram border: IAM, VPC endpoints, KMS, cost controls, and CI/CD.

This sequencing communicates architecture clearly: build path first, then operate path, then governance.

## Failure Scenarios

### Data drift detection + auto-remediation

- **Signal:** Model Monitor detects distribution shift in key features.
- **Immediate action:** CloudWatch alarm fires and opens incident workflow.
- **Remediation:** EventBridge triggers retraining pipeline with fresh data snapshot.

### Model degradation response

- **Signal:** Online precision/recall or proxy business KPI declines.
- **Immediate action:** Shift traffic back using blue/green rollback.
- **Remediation:** Inspect feature attribution drift, retrain with updated sampling/thresholds, re-promote after validation.

### Infrastructure failure recovery

- **Signal:** Endpoint health alarms or elevated 5XX errors.
- **Immediate action:** Scale out healthy variant / fallback to previous production variant.
- **Remediation:** Reconcile infra via Pulumi stack state and re-apply deterministic IaC configuration.

### Cost spike alerting

- **Signal:** Monthly trend exceeds budget guardrail.
- **Immediate action:** Identify top offenders from tagged cost report.
- **Remediation:** Rightsize endpoints, reduce idle environments, increase Spot usage, and enforce cleanup automation.

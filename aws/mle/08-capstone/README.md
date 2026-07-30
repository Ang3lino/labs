# Lab 08 — Capstone (All MLA-C01 Domains)

## Overview

This is THE interview project. It consolidates Labs 01-07 into one end-to-end fraud detection ML system: data ingestion, ETL, feature management, model training, deployment, monitoring, retraining automation, and CI/CD governance. The goal is to demonstrate production-level thinking without introducing new concepts beyond what was already practiced in prior labs.

## Architecture Diagram

```text
┌──────────────────────┐
│     Raw Data (S3)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  ETL (AWS Glue Job)  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ SageMaker Feature    │
│ Store (online/offline)│
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────┐
│ Training (SageMaker PyTorch) │
│ + AMT HPO (Bayesian)         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────┐
│   Model Registry     │
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Deploy                                     │
│ - SageMaker Real-time Endpoint             │
│ - Optional EKS path for container serving  │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Monitor                                    │
│ - SageMaker Model Monitor                  │
│ - SageMaker Clarify                        │
│ - CloudWatch Dashboard + Alarms            │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────┐
│ Retrain Automation                              │
│ EventBridge (S3 PutObject) → SageMaker Pipeline│
└──────────┬──────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐
│  CI/CD (CodePipeline)│
└──────────────────────┘
```

## Key Terms

Top 20 high-yield terms from Labs 01-07 that matter most in this capstone:

1. SageMaker Feature Store (online vs offline)
2. AWS Glue ETL Job
3. Glue Data Catalog
4. Glue Data Quality (DQDL)
5. SageMaker PyTorch Script Mode
6. SageMaker Automatic Model Tuning (AMT)
7. Bayesian hyperparameter optimization
8. SageMaker Model Registry
9. SageMaker Real-time Endpoint
10. Endpoint auto-scaling (InvocationsPerInstance)
11. Blue/green deployment
12. Canary traffic shifting
13. SageMaker Pipelines
14. EventBridge event-driven retraining
15. SageMaker Model Monitor
16. SageMaker Clarify (SHAP explainability)
17. CloudWatch metrics/alarms/dashboards
18. IAM least privilege
19. VPC endpoints (PrivateLink path)
20. KMS encryption at rest

## What Makes This Senior-Level

- **IaC-first architecture:** core infrastructure is provisioned with Pulumi so environments are reproducible and reviewable.
- **Closed-loop MLOps:** model retraining is event-driven from new data arrival, not manual notebook reruns.
- **Production monitoring:** drift and quality controls are explicit (Model Monitor + Clarify + CloudWatch).
- **Security by design:** IAM boundaries, KMS encryption, and private-network controls are designed into the platform.
- **Cost-aware operations:** the stack includes practical optimization levers (Spot training, rightsizing, Savings Plans).

## References

- Lab 01 references (`aws/mle/01-data-pipeline/README.md`)
- Lab 02 references (`aws/mle/02-model-training/README.md`)
- Lab 03 references (`aws/mle/03-bedrock-ai-services/README.md`)
- Lab 04 references (`aws/mle/04-deploy-serve/README.md`)
- Lab 05 references (`aws/mle/05-mlops-pipeline/README.md`)
- Lab 06 references (`aws/mle/06-monitor-secure/README.md`)
- Lab 07 references (`aws/mle/07-book-analysis/README.md`)
- *Machine Learning Design Interview* — Khang Pham
- *Designing Machine Learning Systems* — Chip Huyen (Ch. 7-9)
- AWS Well-Architected ML Lens

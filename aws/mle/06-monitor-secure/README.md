# Lab 06 — Monitor & Secure (Domain 4: Monitoring, Maintenance & Security)

## Theory

In production ML, **data drift**, **concept drift**, and **model drift** are related but different failure modes. **Data drift** means the input feature distribution changes versus training time (for example, average transaction amount shifts upward). **Concept drift** means the relationship between features and labels changes (for example, fraud behavior evolves so old decision boundaries no longer hold). **Model drift** is the resulting drop in model quality over time, observed as degraded precision/recall, latency-quality regressions, or increased business error cost. Data/concept drift can cause model drift, but they are not identical.

In SageMaker, **Model Monitor** provides four monitoring categories: **data quality** (schema/statistics/constraints on inputs), **model quality** (prediction vs ground truth outcomes), **bias drift** (fairness metrics over time), and **feature attribution drift** (changes in importance signals over time). Typical production setup: generate baseline statistics/constraints from training data, schedule monitoring jobs, publish violations to CloudWatch metrics/logs, and wire alarms for triage.

**SageMaker Clarify** complements this by handling post-training bias checks and explainability. For explainability, Clarify calculates **SHAP values** so teams can rank feature contributions and detect when attribution behavior changes in production. Practical pattern: run Clarify after training and periodically after deployment, then compare explainability reports over time.

For deployment safety, teams combine progressive rollouts with **A/B testing** and **shadow variants**. A/B variants split real traffic by weight (for example 90/10), while shadow variants mirror requests to a candidate model without affecting customer responses. This de-risks launches before full cutover.

For observability and operations: **CloudWatch** covers metrics, logs, alarms, and dashboards; **X-Ray** gives distributed tracing to locate latency hotspots; **CloudTrail** records API-level audit events for governance and incident response.

Cost optimization should be built into the ML lifecycle: rightsize endpoint instances using **SageMaker Inference Recommender** and **AWS Compute Optimizer**, use **Spot Instances** for fault-tolerant training, and commit steady workloads via **SageMaker Savings Plans** or **Reserved Instances** where appropriate. Track spend with **AWS Cost Explorer**, enforce guardrails with **AWS Budgets**, and monitor idle/oversized resources through **AWS Trusted Advisor cost checks**.

Security architecture for ML on AWS centers on least privilege and network/data controls. Use **IAM** with minimal execution-role permissions, streamline role governance with **SageMaker Role Manager**, enforce S3 bucket policies, isolate workloads in private subnets with VPC endpoints/PrivateLink, apply **KMS encryption** at rest and TLS in transit, scan sensitive data with **Amazon Macie**, and store credentials in **AWS Secrets Manager** instead of code or plaintext config.

## Key Terms

- `data drift`
- `concept drift`
- `SageMaker Model Monitor`
- `SageMaker Clarify SHAP values`
- `A/B testing shadow variant`
- `CloudWatch alarms`
- `CloudWatch dashboards`
- `AWS X-Ray tracing`
- `CloudTrail`
- `SageMaker Inference Recommender`
- `AWS Compute Optimizer`
- `Spot Instances`
- `SageMaker Savings Plans`
- `IAM execution role`
- `SageMaker Role Manager`
- `VPC endpoint`
- `PrivateLink`
- `KMS encryption`
- `Amazon Macie`
- `AWS Secrets Manager`
- `least privilege principle`
- `AWS Cost Explorer`
- `AWS Trusted Advisor cost checks`
- `AWS Budgets`

## Interview Talking Points

"I set up production monitoring: Model Monitor detects data quality drift and triggers CloudWatch alarms, Clarify generates explainability reports with SHAP values. I configured IAM with least-privilege execution roles, VPC endpoints for SageMaker to avoid public internet, KMS encryption for model artifacts, and cost-optimized training with Spot Instances."

## Exam Tips

Domain 4 is 24% of MLA-C01. Know the 4 types of Model Monitor. Know Clarify post-training vs pre-training. Know cost optimization levers BY NAME. Know VPC endpoint types for SageMaker.

## References

- *Designing ML Systems* Ch.8 (monitoring)
- AWS Well-Architected ML Lens
- AWS Security Best Practices Whitepaper

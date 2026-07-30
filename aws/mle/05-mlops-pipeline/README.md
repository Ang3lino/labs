# Lab 05 — MLOps Pipeline (Domain 3: Deployment & Orchestration)

## Theory

MLOps maturity usually progresses through three levels. **Manual pipelines** depend on ad-hoc notebook runs and human handoffs, so reproducibility and governance are weak. **Automated training pipelines** add repeatable preprocessing/training/evaluation workflows, reducing operational risk and enabling traceability. **Full CI/CD/CT for ML** adds software delivery controls (tests, staged deploys, rollback) plus **continuous training (CT)** triggers when data drift, new data arrivals, or performance regressions are detected.

In SageMaker, **SageMaker Pipelines** provides ML-native orchestration with first-class steps such as `Processing`, `Training`, `Evaluation`, `RegisterModel`, and `Condition`. A common pattern is: run preprocessing, train a model, evaluate metrics, and gate model registration on a threshold (for example, F1 > 0.8). This creates auditable lineage from data inputs to model artifacts and registry versions.

For software delivery around ML assets, **CodePipeline** coordinates stages across source/build/deploy; **CodeBuild** runs validation tests, package steps, and artifact generation via `buildspec.yml`; **CodeDeploy** performs controlled releases with deployment configurations that support traffic shifting and rollback. This separates model quality gates from deployment mechanics while still enabling an end-to-end release path.

**EventBridge** enables event-driven retraining by reacting to upstream signals such as S3 object creation in a `raw/` prefix. Instead of fixed schedules, retraining can start only when meaningful data changes occur, improving freshness/cost balance.

**Step Functions vs SageMaker Pipelines**: Step Functions is a general-purpose cross-service state orchestrator (Lambda, ECS, Glue, SageMaker, SNS, etc.) and is ideal when the workflow spans many AWS services or non-ML branches. SageMaker Pipelines is ML-native and optimized for model lifecycle orchestration with built-in lineage and model registry integration. In practice, teams often use SageMaker Pipelines for the core ML lifecycle and Step Functions for broader platform workflows.

Deployment strategy selection is a risk/speed trade-off. **Blue/green** is safest for production cutover with fast rollback by shifting traffic between old/new environments. **Canary** sends a small percentage first (for example 10% then 100%) to detect issues early with limited blast radius. **Linear** shifts traffic in steady increments to control risk over time. **All-at-once** is fastest and simplest but highest risk, suitable mostly for low-risk internal systems.

Git branching for ML delivery depends on team velocity and governance. **GitFlow** provides strict release/hotfix branches and can help regulated teams, while **trunk-based development** favors frequent small merges, short-lived branches, and faster CI feedback loops. ML teams also need artifact lineage tracking so every deployed model can be traced to code commit, data snapshot, parameters, and approval decision.

## Key Terms

- `SageMaker Pipelines`
- `SageMaker Pipeline steps`
- `AWS CodePipeline`
- `AWS CodeBuild buildspec.yml`
- `AWS CodeDeploy deployment config`
- `blue/green deployment`
- `canary deployment`
- `linear deployment`
- `Amazon EventBridge rules`
- `event-driven retraining`
- `ML model lineage`
- `CI/CD for ML`
- `continuous training (CT)`
- `model approval workflow`
- `SageMaker Projects`
- `AWS Step Functions state machine`
- `Step Functions vs SageMaker Pipelines`

## Interview Talking Points

"I built an end-to-end MLOps pipeline: SageMaker Pipelines orchestrates data processing → training → evaluation → conditional model registration. CodePipeline triggers on model approval, CodeBuild runs tests, CodeDeploy does blue/green deployment. EventBridge triggers retraining when new data lands in S3. I also built a Step Functions state machine for cross-service orchestration."

## Exam Tips

Domain 3.3 is key. Know the difference between SageMaker Pipelines (ML-native, lineage) vs Step Functions (general orchestration). Know CodePipeline stages. Know deployment strategies by name and tradeoff. Know EventBridge rule patterns.

## References

- *Designing ML Systems* Ch.9 (CI/CD for ML)
- AWS MLOps Whitepaper
- Made With ML MLOps module
- MLOps Zoomcamp Module 3

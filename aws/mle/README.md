# AWS MLE Associate (MLA-C01) Study Labs

This repo section contains 8 hands-on labs mapped to all 4 AWS Certified Machine Learning Engineer - Associate (MLA-C01) exam domains, with a Pareto-first focus on high-yield implementation patterns.

## Prerequisites

- AWS account with AWS CLI configured (`aws configure` completed)
- Python 3.11+
- Terraform >= 1.5
- AWS CDK >= 2.x
- Pulumi >= 3.x
- Docker
- kubectl

## Lab overview

| Lab | Domain | Focus | IaC |
| --- | --- | --- | --- |
| 01-data-pipeline | D1: Data Preparation (28%) | S3 → Glue ETL → SageMaker Feature Store, bias detection with Clarify | Terraform |
| 02-model-training | D2: ML Model Development (26%) | PyTorch script mode on SageMaker, HPO with AMT, Model Registry | CDK |
| 03-bedrock-ai-services | D2: ML Model Development (26%) | Bedrock foundation models, RAG with Knowledge Bases, Comprehend, Rekognition, Textract | Terraform |
| 04-deploy-serve | D3: Deployment & Orchestration (22%) | SageMaker endpoints (real-time/serverless/batch), BYOC container, EKS + ECS + Lambda deploy | Pulumi + CDK |
| 05-mlops-pipeline | D3: Deployment & Orchestration (22%) | SageMaker Pipelines, Step Functions, CodePipeline CI/CD, EventBridge triggers, blue/green deploy | CDK |
| 06-monitor-secure | D4: Monitoring & Security (24%) | Model Monitor, Clarify explainability, CloudWatch, X-Ray, IAM, VPC, Cost Explorer, Trusted Advisor | Terraform |
| 07-book-analysis | D1+D2: Data Prep + Model Dev | Psychology/dating book NLP analysis with Comprehend + Bedrock, sentiment, personality traits | Terraform |
| 08-capstone | All domains | End-to-end ML system: data→train→deploy→monitor→retrain, interview-ready project | Pulumi |

## 6-week study timeline

| Week | Labs | Hours/day |
| --- | --- | --- |
| Week 1 | Scaffold + 01-data-pipeline | 1.5-2.0 |
| Week 2 | 02-model-training + start 03-bedrock-ai-services | 1.5-2.0 |
| Week 3 | 03-bedrock-ai-services + 04-deploy-serve | 2.0 |
| Week 4 | 05-mlops-pipeline + 06-monitor-secure | 1.5-2.0 |
| Week 5 | 07-book-analysis | 2.0 |
| Week 6 | 08-capstone + review | 2.0-2.5 |

## Key references

| Type | Resource | Why it helps |
| --- | --- | --- |
| Book | *Designing Machine Learning Systems* (Chip Huyen) | Practical ML system design decisions aligned with exam-style architecture trade-offs |
| Book | *Hands-On ML with Scikit-Learn, Keras & TensorFlow* (Aurélien Géron) | End-to-end model development patterns and reliable implementation details |
| Book | *Machine Learning Design Interview* (Khang Pham) | System design framing for production ML and interview-ready architecture thinking |
| Book | *Machine Learning Engineering with Python* (Andrew P. McMahon) | Implementation-oriented patterns for pipelines, training, and deployment |
| YouTube | StatQuest with Josh Starmer | Intuition-first explanations for core ML and statistics concepts |
| YouTube | Andrej Karpathy "Neural Networks: Zero to Hero" | Deep-learning fundamentals from first principles to practical implementation |
| YouTube | AWS Machine Learning University channel | AWS-native walkthroughs for SageMaker, MLOps, and exam-adjacent services |
| YouTube | DataTalksClub MLOps playlist | Concise operational ML explanations and reproducible exercises |
| Free course | Made With ML (madewithml.com) | Applied ML systems curriculum spanning data, models, deployment, and monitoring |
| Free course | MLOps Zoomcamp (DataTalksClub) | Structured hands-on MLOps practice with reproducible projects |
| Course | AWS Skill Builder: Exam Prep Standard Course - MLA-C01 | Official domain coverage and readiness checks |
| Course | Coursera: Machine Learning Engineering for Production (MLOps) | Strong reinforcement for deployment and monitoring domain skills |

## Quick start

```bash
make setup && cd 01-data-pipeline && python datasets.py --download
```

## Key terms for self-study (MLA-C01 domains)

- Domain 1: Data Preparation for ML (28%)
- Domain 2: ML Model Development (26%)
- Domain 3: Deployment and Orchestration of ML Workflows (22%)
- Domain 4: ML Solution Monitoring, Maintenance, and Security (24%)

## Exam info

- Exam format: 65 questions total (50 scored)
- Passing score: 720 / 1000
- Last day to take MLA-C01 in English: Sept 28, 2026

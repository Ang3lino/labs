# Lab 09: Local → AWS Migration (EKS)

This is the **final capstone lab**: you migrate the Graph RAG + infra-intelligence platform from local Kubernetes into AWS EKS using Terraform.

> ⚠️ **COST WARNING (READ FIRST):** EKS is not free-tier friendly. Expect ~**$158/month** while resources are running. Treat this as an ephemeral lab and destroy everything after verification.

## Scenario

You've built and tested your platform locally. Your CTO says: _"This is impressive. Put it in production on AWS by Friday."_

Your task is to migrate Labs 07-08 from Docker Desktop Kubernetes to Amazon EKS with AWS-native building blocks: ECR for images, ALB Ingress for traffic, and EBS-backed persistent storage for Neo4j.

## What You'll Learn

- How local K8s primitives map to production AWS equivalents
- How to provision VPC + EKS + ECR with readable Terraform
- How to update manifests for ALB ingress and EBS storage classes
- How to use IRSA foundations (OIDC provider) for secure pod-to-AWS access
- How to estimate, monitor, and aggressively clean up cloud costs

## Architecture Diagram (ASCII)

```text
LOCAL                           AWS
─────                           ───
Docker Desktop K8s    →    EKS (managed control plane)
Local Docker images   →    ECR (container registry)
NodePort services     →    ALB Ingress Controller
Local PVCs            →    EBS CSI Driver + gp3 volumes
kubectl (local)       →    kubectl (via aws eks update-kubeconfig)
K8s Secrets           →    AWS Secrets Manager + External Secrets Operator
Neo4j StatefulSet     →    Same, but on EBS persistent volumes
```

## Local → AWS Mapping

| Local K8s | AWS Equivalent | Why |
|-----------|---------------|-----|
| Docker Desktop cluster | EKS | Managed control plane, no maintenance |
| docker build + local images | ECR | Private registry, integrated with EKS |
| NodePort | ALB + Ingress | Production-grade load balancing |
| hostPath/local PVC | EBS gp3 | Durable, snapshotable block storage |
| kubectl port-forward | ALB DNS | Real endpoints |
| K8s Secrets | Secrets Manager | Rotation, audit, IAM integration |

## Prerequisites

- AWS account with IAM permissions for VPC/EKS/ECR/IAM
- Terraform >= 1.6
- `aws` CLI configured (`aws configure`)
- `kubectl`
- Docker
- Python 3 (used by helper scripts for lightweight JSON parsing)

```bash
aws sts get-caller-identity
terraform -version
kubectl version --client
docker version
python3 --version
```

## Step-by-Step Instructions

From this lab directory:

```bash
cd k8s/labs/09-aws-migration
```

### Step 1: Create ECR repositories + push images

```bash
cd terraform
terraform init
terraform apply -target=aws_ecr_repository.repositories -auto-approve
cd ..
bash scripts/push-images.sh
```

### Step 2: Provision EKS cluster with Terraform

```bash
cd terraform
terraform apply
cd ..
```

### Step 3: Configure kubectl for EKS

```bash
cd terraform
terraform output -raw kubectl_config_command
cd ..
# Run the printed command
```

### Step 4: Install AWS Load Balancer Controller

```bash
bash scripts/deploy.sh
```

`deploy.sh` installs the controller using upstream manifests.

### Step 5: Install EBS CSI Driver

`deploy.sh` also applies the stable EBS CSI manifests so `ebs.csi.aws.com` can provision PVCs.

### Step 6: Update K8s manifests for AWS (Ingress, StorageClass, etc.)

Use the manifests in `k8s-aws/`:

- `storageclass.yaml` for gp3 EBS
- `neo4j-statefulset.yaml` for EBS-backed Neo4j
- `ingress.yaml` for ALB routing (`/query`, `/graph`)

### Step 7: Deploy to EKS

```bash
bash scripts/deploy.sh
```

### Step 8: Verify everything works

```bash
kubectl -n graph-rag get pods
kubectl -n graph-rag get ingress graph-rag-ingress
kubectl -n graph-rag get pvc
```

If Labs 07/08 services are deployed (`query-api`, `rag-api`), test via ALB DNS:

```bash
ALB=$(kubectl -n graph-rag get ingress graph-rag-ingress -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl "http://${ALB}/query"
curl "http://${ALB}/graph/health"
```

### Step 9: CLEANUP (destroy to avoid charges)

```bash
bash scripts/destroy.sh
```

> ⚠️ **CRITICAL:** Do not leave EKS running overnight unless you intentionally accept ongoing cost.

## Cost Estimates (Lab-Scale)

- EKS control plane: ~**$72/mo**
- 2x `t3.medium` nodes: ~**$60/mo**
- EBS volumes: ~**$5/mo**
- ALB: ~**$20/mo**
- ECR storage: ~**$1/mo**

### Estimated Total: ~**$158/mo**

> ⚠️ **DESTROY AFTER TESTING.** Running this for a full month without cleanup is unnecessary for a lab.

## Intentional Simplifications

- `# ponytail:` single NAT gateway is used to reduce lab cost (not HA production pattern).
- `# ponytail:` ECR tag mutability is `MUTABLE` for quick iteration.
- `# ponytail:` controller installs use direct upstream manifests to keep focus on migration concepts.

## Interview Talking Points

- "I migrated a local K8s ML platform to production AWS EKS using Terraform for infrastructure and ECR for container images."
- "I understand the mapping between local K8s primitives and their AWS equivalents."
- "I implement proper IAM roles for service accounts (IRSA) for secure AWS service access from pods."
- "I can estimate and optimize cloud costs for ML infrastructure."

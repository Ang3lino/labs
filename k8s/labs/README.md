# K8s Labs for AI/ML Engineers

**From notebook to production. From local to AWS. From "I know Docker" to "I run ML platforms."**

## Who This Is For

You're a Sr. AI/ML Engineer who:
- Trained models in notebooks, never deployed one
- Knows Docker, Terraform, AWS, Python
- Keeps seeing K8s on job postings and wants to actually get it
- Wants portfolio pieces that prove production ML skills to recruiters

## Prerequisites

- Docker Desktop with Kubernetes enabled (Settings → Kubernetes → Enable)
- `kubectl` CLI installed
- Python 3.10+
- Basic Docker knowledge (Dockerfile, `docker build`, `docker run`)

```bash
# Verify your setup
kubectl version --client
docker version
python --version
```

## Learning Path

```
 FUNDAMENTALS                INTERMEDIATE               CAPSTONE
 (K8s basics via ML)         (Real-world patterns)      (Portfolio project)
 ┌──────────────┐            ┌──────────────┐           ┌──────────────────────┐
 │ 01 Deploy    │            │ 04 Rolling   │           │ 07 Graph RAG         │
 │    ML Model  │──────┐     │    Updates   │──────┐    │     on K8s (Local)   │
 └──────────────┘      │     └──────────────┘      │    └──────────────────────┘
 ┌──────────────┐      │     ┌──────────────┐      │    ┌──────────────────────┐
 │ 02 Self-     │──────┤     │ 05 ML        │──────┤    │ 08 Infra Intelligence│
 │    Healing   │      │     │    Pipeline  │      │    │    (ECS Log Analysis)│
 └──────────────┘      │     └──────────────┘      │    └──────────────────────┘
 ┌──────────────┐      │     ┌──────────────┐      │    ┌──────────────────────┐
 │ 03 Auto-     │──────┘     │ 06 Training  │──────┘    │ 09 Local → AWS       │
 │    Scaling   │            │    Jobs      │           │    Migration (EKS)   │
 └──────────────┘            └──────────────┘           └──────────────────────┘
```

## Lab Structure

Every lab follows the same pattern:

```
lab-XX-name/
├── README.md          # Scenario, what you learn, steps, interview talking points
├── app.py             # Application code (FastAPI + ML)
├── Dockerfile         # Container image
├── requirements.txt   # Python deps
└── k8s/               # Kubernetes manifests
    ├── deployment.yaml
    └── service.yaml
```

## Labs Overview

| # | Lab | K8s Concepts | Interview Signal |
|---|-----|-------------|-----------------|
| 01 | Deploy ML Model | Pod, Deployment, Service | "I can take a model from notebook to production" |
| 02 | Self-Healing Inference | Probes, RestartPolicy | "My services recover automatically" |
| 03 | Auto-Scaling Under Load | HPA, Resources | "I handle traffic spikes without manual intervention" |
| 04 | Zero-Downtime Updates | Rolling updates, Rollback | "I deploy new models without dropping requests" |
| 05 | ML Pipeline Services | Multi-service, DNS, ConfigMaps | "I build microservice ML architectures" |
| 06 | Training Jobs | Jobs, CronJobs, PVCs | "I orchestrate training at scale" |
| 07 | Graph RAG on K8s | StatefulSet, Namespaces, Secrets | "I deploy complex AI systems on K8s" |
| 08 | Infra Intelligence | Jobs, real-world data, Graph queries | "I build AI that monitors infrastructure" |
| 09 | Local → AWS | EKS, ECR, IAM, Terraform | "I migrate from local K8s to production cloud" |

## How to Use These Labs

1. **Do them in order** — each builds on concepts from the previous
2. **Break things on purpose** — delete pods, kill containers, overload services
3. **Read the interview talking points** — each lab teaches you what to say
4. **Push to GitHub** — this IS your portfolio

## Quick Reference

```bash
# The 10 commands you'll use in every lab
kubectl apply -f k8s/              # Deploy everything in k8s/ directory
kubectl get pods                   # What's running?
kubectl get all                    # Everything: pods, services, deployments
kubectl logs <pod-name>            # See stdout/stderr
kubectl describe pod <pod-name>    # Detailed info + events
kubectl exec -it <pod-name> -- sh  # Shell into a container
kubectl delete pod <pod-name>      # Kill a pod (watch it come back)
kubectl scale deployment <name> --replicas=N
kubectl rollout undo deployment <name>
kubectl delete -f k8s/             # Tear everything down
```

# Study Plan — HPE On-Prem AI Inference Platform

## Your Context

- **Project:** HPE On-Prem AI Inference Platform (LLM-as-a-Service)
- **Timeline:** Aug 1 – Oct 31, 2026 (13 weeks) + Nov hyper-care
- **Hardware:** ProLiant DL380a Gen12, NVIDIA H200 NVL + L40S GPUs
- **Sites:** Fort Collins (primary) + Houston (HA/DR)
- **Your role:** Apex Systems engineer delivering the full software stack

## Priority Tiers

Everything is ranked by **how soon it blocks delivery** and **how much of the project depends on it**.

---

## Tier 1 — Must Know Before Week 4 (Foundation Phase)

These are the baseline technologies already running. You'll touch them daily.

| # | Topic | Why It's Blocking | Study Target | Time |
|---|---|---|---|---|
| 1 | **Kubernetes (upstream, not OpenShift)** | Every component runs on K8s. CLS-1 through CLS-5 require cluster stand-up as code. | Deployments, Services, StatefulSets, DaemonSets, RBAC, ResourceQuotas, Namespaces, PVCs, NetworkPolicy. Multi-cluster patterns. | 10h |
| 2 | **Proxmox** | Hypervisor for control plane VMs (GPU workers are bare metal). INF-3 says automation aligns to Proxmox+Ubuntu+Ansible. | VM provisioning, templates, cloud-init, storage pools, networking bridges, GPU passthrough to bare metal workers. | 4h |
| 3 | **NVIDIA GPU Operator + Device Plugin** | GPU scheduling on K8s. Required for every inference workload. Every epic from 05 onward needs GPUs scheduled correctly. | Install operator, verify GPU discovery, node labeling (H200 vs L40S), MIG if applicable, time-slicing, DCGM exporter for metrics. | 4h |
| 4 | **KubeRay + Ray Serve** | Baseline technology. Epics 05 (inference) and 06 (ModelOps) depend on it. RayCluster, RayService, RayJob CRDs already in the prototype. | Operator install, RayCluster lifecycle, RayService with Serve graphs, worker group autoscaling (min/max/idleTimeout), head pod networking, Ray dashboard. | 8h |
| 5 | **vLLM** | The inference engine. Epic 05 core deliverable. Already baseline with gpt-oss-120b, gpt-oss-20b, Gemma variants. | Serve via Ray distributed backend (`--distributed-executor-backend ray`), tensor parallelism, pipeline parallelism, PagedAttention, continuous batching, OpenAI-compatible API, GPU memory utilization tuning. | 6h |
| 6 | **Ansible** | Host configuration and firmware baselines (baseline tech). INF-3 automation. | Playbooks for node prep, GPU driver install, kernel params, NFS mounts, SSH hardening. Enough to read/modify existing playbooks, not write from scratch. | 3h |
| 7 | **Terraform** | Infrastructure provisioning (baseline). Proxmox provider for VM creation, potentially network/DNS. | Proxmox provider, state management, modules for cluster provisioning. Enough to read/modify, not architect from scratch. | 3h |

**Tier 1 total: ~38h** — front-load this in weeks 1-3.

---

## Tier 2 — Must Know Before Week 7 (Parallel Build-Out)

These are "New" or critical technologies for the parallel epics (4-10).

| # | Topic | Why It's Blocking | Study Target | Time |
|---|---|---|---|---|
| 8 | **MLflow** | Baseline. Epic 06 (ModelOps). Model registry, versioning, promotion, rollback (MDL-1 through MDL-6). Already running on PostgreSQL. | Model Registry workflow (aliases, NOT stages), `copy_model_version()`, webhooks for CI/CD, artifact storage on SeaweedFS (S3-compatible), tracking server on PostgreSQL, Prometheus metrics. | 5h |
| 9 | **SeaweedFS** | New. Replaces MinIO (archived). S3-compatible object storage for artifacts, model weights, data lake. Used by MLflow, Iceberg, and the ingestion pipeline. | weed master/volume/filer/s3 architecture, S3 API compatibility, bucket policies, replication for HA/DR (Fort Collins to Houston), Iceberg REST catalog on port 8181. | 6h |
| 10 | **Argo Workflows + Argo Events** | New. Replaces Airflow. Pipeline execution (Epic 08 RAG, data ingestion). Argo Events for SQS EventSource triggering workflows on S3 object events. | Workflow CRD, container-per-step model, DAG templates, CronWorkflow for reconciliation, Argo Events Sensor + EventSource (SQS), parameter passing, artifact handling. | 6h |
| 11 | **GitOps (GitHub Actions + Argo CD)** | K8S-2 mandates GitOps. Current baseline is GitHub Actions with Helm. Argo CD is the target direction. | Helm-driven deployments from GitHub Actions (current), Argo CD ApplicationSet/sync waves/self-heal (target). Repo structure: infra repos separated from app repos (K8S-3). | 5h |
| 12 | **PostgreSQL (multi-role)** | Baseline. Single instance serves MLflow backend, SeaweedFS filer, pgvector, and Apache AGE. Assumption 11 says this needs load-testing. | Connection pooling (PgBouncer), extensions (pgvector HNSW indexes, Apache AGE openCypher), backup/restore, replication for HA/DR, resource isolation between workloads. | 5h |
| 13 | **pgvector** | New. RAG-4 requires vector index for retrieval. Same Postgres instance. | HNSW index creation, embedding dimensions, similarity search queries, performance tuning (ef_construction, m), comparison threshold vs Qdrant (which is the Open fallback). | 3h |
| 14 | **nginx Ingress** | Baseline. API-1 through API-4. External API and platform service access. OpenAI-compatible endpoint routing. | Ingress rules, TLS termination, rate limiting (Epic 07 API quotas), path-based routing to multiple model endpoints, upstream configuration for vLLM/Ray Serve. | 3h |
| 15 | **Okta integration** | Baseline external dependency. IAM-1 (identity). Per-user chat history keyed on uid claim. | OIDC flow with K8s (DEX or direct), token validation at ingress/API gateway, claim extraction for tenant isolation and audit logging. | 3h |
| 16 | **Flannel + MetalLB** | Baseline networking. Pod network (Flannel) + BGP load balancer (MetalLB) shared across 3 clusters. | Flannel VXLAN/host-gw modes, MetalLB BGP mode config (shared VIP across clusters), troubleshooting pod networking, cross-cluster service discovery. | 3h |

**Tier 2 total: ~39h** — study during weeks 3-6 while building.

---

## Tier 3 — Must Know Before Week 10 (Validate & Harden)

These support the hardening, HA/DR, security, and acceptance epics.

| # | Topic | Why It's Blocking | Study Target | Time |
|---|---|---|---|---|
| 17 | **HA/DR patterns** | Epic 14. HADR-1 through HADR-8. Fort Collins to Houston replication, failover drill, RPO/RTO documentation. | Cross-site SeaweedFS replication, PostgreSQL streaming replication or logical replication, model weight sync, K8s cluster federation or GitOps-driven multi-cluster, failover runbook structure. | 6h |
| 18 | **Prometheus + Grafana + VictoriaLogs + Alertmanager** | Baseline. Epic 11 (Observability). OBS-1 through OBS-5 require 4 dashboard categories. Already running but needs hardening. | ServiceMonitor/PodMonitor for Ray Serve metrics, GPU DCGM metrics, custom Grafana dashboards (infra/app/platform/business), VictoriaLogs as log data source, Alertmanager routing to PagerDuty, SLO-based alerts. | 5h |
| 19 | **Apache Iceberg + Apache Doris** | New. Data lake layer. Iceberg tables over SeaweedFS, Doris as analytical store with browser upload (port 8030). | Iceberg table format basics, REST catalog, partition evolution. Doris FE/BE architecture, browser upload, Grafana data source. Enough to validate the data pipeline, not build from scratch. | 4h |
| 20 | **Apache Spark on K8s** | New/Open. SparkApplication CRD for CPU-bound transforms (raw bucket to Iceberg tables). Status is "Open" between Kubeflow v2.5.1 and Apache 0.9.0 operators. | SparkApplication CRD basics, driver/executor pod lifecycle, S3 (SeaweedFS) integration, Iceberg writer configuration. Compare the two operator CRD APIs. | 4h |
| 21 | **Security hardening** | Epic 10. RBAC, tenant isolation, audit logging, secrets management, GOV-1 through GOV-6. | K8s RBAC policies, namespace isolation, NetworkPolicy per tenant, Secret management (External Secrets or SealedSecrets), prompt/response logging for audit trail, pod security standards. | 4h |
| 22 | **Apache AGE** | New. Property graph traversal on PostgreSQL. openCypher queries for knowledge graph / RAG enrichment. | Extension install, CREATE GRAPH, basic openCypher (MATCH/CREATE/RETURN), integration with the RAG pipeline. Enough to validate, not master. | 2h |
| 23 | **ai-tunnel / ai-relay** | Baseline. Outbound mTLS transport toward consuming teams. Bedrock-compatible fallback routing. | mTLS configuration, certificate management, routing rules to upstream (AWS Bedrock fallback if approved), health checks. Read existing code/config, don't rebuild. | 2h |

**Tier 3 total: ~27h** — study during weeks 7-10 alongside validation work.

---

## Tier 4 — Nice to Have / Deepen as Needed

| # | Topic | When | Time |
|---|---|---|---|
| 24 | **Qdrant** | Only if pgvector misses retrieval targets (status: Open) | 3h |
| 25 | **Ray Data** | Embedding generation and dataset evaluation — already baseline, learn when touching RAG pipeline | 3h |
| 26 | **Kubeflow Spark Operator vs Apache Spark Operator** | When the "Open" decision is made (compare CRDs) | 2h |
| 27 | **NVIDIA NIM / Triton** | Alternative serving runtimes mentioned in scope — learn when/if the team decides to use them alongside vLLM | 3h |

---

## Study Strategy

**Total estimated study: ~115h across 13 weeks (~9h/week)**

```
Wk 1-3   ████████████████████████████  Tier 1 (38h) — foundations
Wk 3-6   ██████████████████████████     Tier 2 (39h) — parallel build
Wk 7-10  ███████████████████            Tier 3 (27h) — harden
Wk 10+   ████████                       Tier 4 (11h) — as needed
```

**How to study each topic:**
1. Read official docs for 30 min to understand concepts
2. Do the relevant lab from the `mlops-infra/` directory (labs cover K8s, GPU, vLLM, KServe, observability, Argo CD, KubeRay)
3. Read the existing prototype code/configs — this project has a working baseline, so read before you build
4. Practice on minikube/kind locally for anything hands-on

**Priority rule:** If two topics compete for time, pick the one that unblocks someone else on the team. The project runs 12 parallel workstreams — blocking dependencies are the real risk.

## Mapping to Labs

| Study Topic | Lab |
|---|---|
| Kubernetes | `mlops-infra/02-kubernetes-core` |
| GPU Operator | `mlops-infra/03-gpu-kubernetes` |
| vLLM + KServe | `mlops-infra/04-vllm-model-serving` |
| RAG + pgvector | `mlops-infra/05-rag-vector-search` |
| Prometheus + Grafana | `mlops-infra/06-observability` |
| Argo CD + GitOps | `mlops-infra/07-argocd-gitops` |
| KubeRay + Ray Serve | `mlops-infra/08-kuberay-distributed-inference` |
| Containers (review) | `mlops-infra/01-containers` |

## Mapping to Project Epics

| Epic | Key Technologies | Tier |
|---|---|---|
| 01-02: Governance, Access | Jira, VPN, Okta | 2 |
| 03: Architecture & Capacity | All of Tier 1 | 1 |
| 04: Platform Substrate | K8s, Proxmox, GPU Operator, Ansible, Terraform | 1 |
| 05: Inference Serving | KubeRay, Ray Serve, vLLM, nginx Ingress | 1 |
| 06: ModelOps & Registry | MLflow, SeaweedFS | 2 |
| 07: API Gateway & Auth | nginx Ingress, Okta, rate limiting | 2 |
| 08: RAG Platform | Argo Workflows, pgvector, Ray Data, SeaweedFS | 2 |
| 09: Reservation & Showback | K8s ResourceQuotas, custom metering | 2 |
| 10: Security | RBAC, NetworkPolicy, secrets, audit logging | 3 |
| 11: Observability | Prometheus, Grafana, VictoriaLogs, Alertmanager | 3 |
| 12: Pilot Onboarding | All serving + API stack | 2-3 |
| 13: QA & Acceptance | Load testing, failure modes | 3 |
| 14: HA/DR | SeaweedFS replication, Postgres replication, failover | 3 |
| 15: Documentation & KT | Architecture docs, runbooks | 3 |
| 16: Closure & Hyper-care | All | 3 |

## Technology Assumptions Reference

The project maintains a living document of technology assumptions. Key decisions that affect your study:

- **MinIO is retired** — replaced by SeaweedFS (repository archived 2026-04-25)
- **Airflow is retired** — replaced by Argo Workflows + Argo Events
- **ClickHouse is retired** — replaced by Apache Doris
- **MLflow stages API is deprecated** — use aliases (@champion/@baseline)
- **Spark operator is Open** — decision pending between Kubeflow v2.5.1 and Apache 0.9.0
- **Qdrant is Open** — fallback if pgvector misses retrieval targets
- **GPU fleet is mixed** — H200 NVL (large models) + L40S (smaller models), plan node affinity accordingly

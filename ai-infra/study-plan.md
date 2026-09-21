# Study Plan — On-Prem AI Inference Platform

## Your Context

- **Project:** On-Prem AI Inference Platform (LLM-as-a-Service)
- **Timeline:** 13 weeks + hyper-care
- **Hardware:** ProLiant DL380a Gen12, NVIDIA H200 NVL + L40S GPUs
- **Sites:** Primary + HA/DR
- **Your role:** Platform engineer delivering the full software stack

## Priority Tiers

Everything is ranked by **how soon it blocks delivery** and **how much of the project depends on it**.

---

## Tier 1 — Must Know Before Week 4 (Foundation Phase)

These are the baseline technologies already running. You'll touch them daily.

| # | Topic | Why It's Blocking | Study Target | Time |
| --- | --- | --- | --- | --- |
| 1 | **Kubernetes (upstream)** | Every component runs on K8s. Requires cluster stand-up as code. | Deployments, Services, StatefulSets, DaemonSets, RBAC, ResourceQuotas, Namespaces, PVCs, NetworkPolicy. Multi-cluster patterns. | 10h |
| 2 | **Proxmox** | Hypervisor for control plane VMs. | VM provisioning, templates, cloud-init, storage pools, networking bridges, GPU passthrough. | 4h |
| 3 | **NVIDIA GPU Operator + Device Plugin** | GPU scheduling on K8s. Required for every inference workload. | Install operator, verify GPU discovery, node labeling (H200 vs L40S), MIG if applicable, time-slicing, DCGM exporter for metrics. | 4h |
| 4 | **KubeRay + Ray Serve** | Baseline technology. | Operator install, RayCluster lifecycle, RayService with Serve graphs, worker group autoscaling, head pod networking. | 8h |
| 5 | **vLLM** | The inference engine. | Serve via Ray distributed backend, tensor parallelism, pipeline parallelism, PagedAttention, continuous batching, OpenAI-compatible API, GPU memory utilization tuning. | 6h |
| 6 | **Ansible** | Host configuration and firmware baselines. | Playbooks for node prep, GPU driver install, kernel params, NFS mounts, SSH hardening. | 3h |
| 7 | **Terraform** | Infrastructure provisioning (baseline). | Proxmox provider, state management, modules for cluster provisioning. | 3h |

**Tier 1 total: ~38h** — front-load this in weeks 1-3.

---

## Tier 2 — Must Know Before Week 7 (Parallel Build-Out)

These are "New" or critical technologies for the parallel epics.

| # | Topic | Why It's Blocking | Study Target | Time |
| --- | --- | --- | --- | --- |
| 8 | **MLflow** | Baseline. Model registry, versioning. | Model Registry workflow, webhooks for CI/CD, artifact storage on SeaweedFS, tracking server on PostgreSQL, Prometheus metrics. | 5h |
| 9 | **SeaweedFS** | New. Replaces MinIO. S3-compatible object storage. | weed master/volume/filer/s3 architecture, S3 API compatibility, bucket policies, replication for HA/DR, Iceberg REST catalog. | 6h |
| 10 | **Argo Workflows + Argo Events** | New. Replaces Airflow. Pipeline execution. | Workflow CRD, container-per-step model, DAG templates, CronWorkflow, Argo Events Sensor + EventSource (SQS). | 6h |
| 11 | **GitOps (GitHub Actions + Argo CD)** | Mandates GitOps. Current baseline is GitHub Actions with Helm. | Helm-driven deployments from GitHub Actions (current), Argo CD ApplicationSet/sync waves/self-heal (target). | 5h |
| 12 | **PostgreSQL (multi-role)** | Baseline. Single instance serves MLflow backend, SeaweedFS filer, pgvector, and Apache AGE. | Connection pooling (PgBouncer), extensions, backup/restore, replication for HA/DR, resource isolation between workloads. | 5h |
| 13 | **pgvector** | New. Requires vector index for retrieval. | HNSW index creation, embedding dimensions, similarity search queries, performance tuning. | 3h |
| 14 | **nginx Ingress** | Baseline. External API and platform service access. | Ingress rules, TLS termination, rate limiting, path-based routing, upstream configuration for vLLM/Ray Serve. | 3h |
| 15 | **Okta integration** | Baseline external dependency. IAM (identity). | OIDC flow with K8s, token validation at ingress/API gateway, claim extraction for tenant isolation and audit logging. | 3h |
| 16 | **Flannel + MetalLB** | Baseline networking. Pod network (Flannel) + BGP load balancer. | Flannel VXLAN/host-gw modes, MetalLB BGP mode config, troubleshooting pod networking. | 3h |

**Tier 2 total: ~39h** — study during weeks 3-6 while building.

---

## Tier 3 — Must Know Before Week 10 (Validate & Harden)

These support the hardening, HA/DR, security, and acceptance epics.

| # | Topic | Why It's Blocking | Study Target | Time |
| --- | --- | --- | --- | --- |
| 17 | **HA/DR patterns** | Primary to Secondary replication, failover drill, RPO/RTO documentation. | Cross-site SeaweedFS replication, PostgreSQL streaming replication or logical replication, model weight sync, K8s cluster federation. | 6h |
| 18 | **Prometheus + Grafana + VictoriaLogs + Alertmanager** | Baseline. Observability. | ServiceMonitor/PodMonitor for Ray Serve metrics, GPU DCGM metrics, custom Grafana dashboards, VictoriaLogs, Alertmanager routing, SLO-based alerts. | 5h |
| 19 | **Apache Iceberg + Apache Doris** | New. Data lake layer. | Iceberg tables over SeaweedFS, Doris as analytical store. | 4h |
| 20 | **Apache Spark on K8s** | New/Open. SparkApplication CRD for CPU-bound transforms. | SparkApplication CRD basics, driver/executor pod lifecycle, S3 (SeaweedFS) integration, Iceberg writer configuration. | 4h |
| 21 | **Security hardening** | RBAC, tenant isolation, audit logging, secrets management. | K8s RBAC policies, namespace isolation, NetworkPolicy per tenant, Secret management, prompt/response logging, pod security standards. | 4h |
| 22 | **Apache AGE** | New. Property graph traversal on PostgreSQL. | Extension install, CREATE GRAPH, basic openCypher, integration with the RAG pipeline. | 2h |
| 23 | **ai-tunnel / ai-relay** | Baseline. Outbound mTLS transport toward consuming teams. | mTLS configuration, certificate management, routing rules, health checks. | 2h |

**Tier 3 total: ~27h** — study during weeks 7-10 alongside validation work.

---

## Tier 4 — Nice to Have / Deepen as Needed

| # | Topic | When | Time |
| --- | --- | --- | --- |
| 24 | **Qdrant** | Only if pgvector misses retrieval targets (status: Open) | 3h |
| 25 | **Ray Data** | Embedding generation and dataset evaluation — already baseline, learn when touching RAG pipeline | 3h |
| 26 | **Kubeflow Spark Operator vs Apache Spark Operator** | When the "Open" decision is made (compare CRDs) | 2h |
| 27 | **NVIDIA NIM / Triton** | Alternative serving runtimes mentioned in scope — learn when/if the team decides to use them alongside vLLM | 3h |

---

## Study Strategy

Total estimated study: ~115h across 13 weeks (~9h/week)

How to study each topic:

1. Read official docs for 30 min to understand concepts
2. Do the relevant lab from the `mlops-infra/` directory (labs cover K8s, GPU, vLLM, KServe, observability, Argo CD, KubeRay)
3. Read the existing prototype code/configs — this project has a working baseline, so read before you build
4. Practice on minikube/kind locally for anything hands-on

## Technology Assumptions Reference

The project maintains a living document of technology assumptions. Key decisions that affect your study:

- **MinIO is retired** — replaced by SeaweedFS
- **Airflow is retired** — replaced by Argo Workflows + Argo Events
- **ClickHouse is retired** — replaced by Apache Doris
- **MLflow stages API is deprecated** — use aliases (@champion/@baseline)
- **Spark operator is Open** — decision pending between Kubeflow v2.5.1 and Apache 0.9.0
- **Qdrant is Open** — fallback if pgvector misses retrieval targets
- **GPU fleet is mixed** — H200 NVL (large models) + L40S (smaller models), plan node affinity accordingly

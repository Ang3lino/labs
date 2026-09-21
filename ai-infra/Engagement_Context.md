# On-Prem AI Platform — Engagement Context

**Purpose:** Condensed technical context for agents working in this repo.
**Use it for:** Understanding who owns what, what is decided vs open, and which constraint any new document must respect.

## 1. The engagement in one paragraph

The Platform Team is building an on-prem AI/LLM inference platform for the Client's Compute Engineering org. The Platform Team owns the platform: Kubernetes, LLM-as-a-Service, inference endpoints, training pipelines, observability, API exposure, and the data lake *platform layer*. The Client owns hardware, base OS, the models and training logic, and the data itself. The build is compressed with parallel workstreams. Milestone M3 — reservation + showback, pilot, security evidence pack — is the primary target.

## 2. Source inventory

| File | What it is |
| --- | --- |
| `SOW_Redacted.md` | Statement of work, deliverables, acceptance criteria, milestones |
| `AI_Platform_Requirements_v2.md` | Requirements, incl. section 9 Reservation & Capacity Management |
| `AI_Platform_Kickoff.md` | Kickoff deck, workstreams WS1–WS7, milestone dates |
| `Technology_Assumptions.md` | Per-technology assumption register with Baseline / New / Open status |

## 3. Workshop timeline and what each settled

| Session | Outcome that matters |
| --- | --- |
| Discovery workshop | Action log established; hardware-delay risk raised; ~800-engineer figure flagged as *not* a concurrency number |
| Architecture Overview | Scope and ownership split agreed; GitOps preferred; Cloud AI-Relay out of Platform Team scope |
| Infrastructure & Platform | Hardware inventory; start on local storage, SAN later; OpenBAO for secrets |
| AI Subnet Architecture | Recommends isolating the AI solution in a sandbox, in-band / out-of-band split |
| Okta workshop | Identity constraints and the schedule risk |
| Data lake workshop | Sizing revised upward, MinIO EOL, Ceph RGW vs SeaweedFS |

## 4. Ownership boundary (Firm)

**Platform Team owns:** Kubernetes deployment and cluster config; LLM-as-a-Service; model training pipelines; inference endpoint deployment; observability, monitoring, alerting; API exposure and access patterns; data lake *platform* components; storage infrastructure and service availability.

**Client owns:** hardware and base OS provisioning; existing platform assets and repositories; model development teams and training logic; data ingestion, population, schema, table management, dataset preparation; existing integrations.

**Explicitly out of scope:** Cloud failover, relay/tunnel integration work; data curation and preparation pipelines; a full developer experience; the inline security appliance.

## 5. Hardware reality — the binding constraint

- **Three servers** assigned. Two DL380a's **not yet online**; one DL380 (**"GPU1"**) is online.
- GPU1: upgraded to **three L40S GPUs**, ~21 TB local storage, Ubuntu installed.
- GPU1 has **1 Gig networking only**. 10 Gig needs a Gen 12 NIC, limited inventory.
- Storage: redundant SAN. Drives ~15–16 TB each, 12 per server. **SAN is not required to start** — begin on local storage, add HBAs later.
- Top-of-rack: L2 switch, managed via labs as a service. **No upstream access, no PAN/WAF appliances today.**
- **NVLink — resolved.** **The L40S does not support NVLink at all**. All inter-GPU traffic on GPU One goes over **PCIe Gen4 x16 at 64 GB/s**. **MIG is likewise unsupported on L40S**, so GPU isolation cannot be hardware-enforced.

> **Reconciled:** The fleet is **3 × L40S on one host, PCIe-only, no bridge**. Tensor parallelism at TP=2 runs over PCIe and is a *capacity* mechanism for models exceeding 48 GB, not a latency optimisation — prefer TP=1 with one replica per GPU.

## 6. Identity — the single largest schedule risk

- **Okta = authentication/SSO only. SailPoint = authorization, groups, roles.**
- Both SAML and OIDC supported; **OIDC is the preferred path**.
- **No direct admin or API access** to workforce IAM. Everything is ticket-based.
- **Every authenticated component needs its own ID** before SSO can be configured — Grafana, Ray, MinIO, MLflow each require a separate request and security review.
- Cluster/workload service identities (cron, Kubernetes) **sit outside Okta** and need a separate design.

## 7. Data lake

- Scale: **~800 engineers, ~50% peak concurrency (~400 simultaneous)**. **Use ~181 TB** as the current footprint, growing **~15%/yr**, default **3-year retention**.
- Example workload: 2–10 MB files today, up to 100 MB future; ~10K files/day rising to ~50K; **80–100 GB/day**.
- **MinIO is end-of-life.** An S3-compatible replacement is required. Candidates: **SeaweedFS** vs **Ceph RGW**.

> **Reconciled:** SeaweedFS is the working assumption; Ceph RGW is the live challenger; the evaluation is open.

## 8. Security posture

- **Network isolation recommended**: put the AI solution in a sandbox, out-of-band network for admin/iLO and in-band for LLM application services.
- **PII handling undecided**: inline appliance before data enters the lake vs. handling at the ingestion layer.
- **Secrets: OpenBAO** on-prem vault as source of truth, exported into Kubernetes short-term.
- Access reviews today are Okta + SailPoint + custom scripts with weekly reporting.

## 9. Open questions carried forward

| Question |
| --- |
| Real concurrency per tier (prod / pilot / dev) |
| Will on-order GPU hardware delay the build? |
| Token-based vs GPU-based quota/allocation |
| Data lake team ownership vs AI Infra team |
| Custom guardrail requirements beyond standard PII/security |
| Global API endpoint strategy, DNS, cross-site failover |
| Developer experience model — Jupyter, GitHub-driven, containerized. **No approach selected.** |
| Enterprise source control standards and supported CI/CD patterns |
| Ceph RGW vs SeaweedFS given MinIO EOL |
| IAM API Access Management, rate limits, privileged service-account controls |

## 10. Working conventions

- A **master action item / decision log** is the single source of truth into architecture finalization.
- The technology assumptions register uses **Baseline / New / Open** status. Anything marked Open is a decision waiting to be made, not a gap.

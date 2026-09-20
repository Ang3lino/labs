# Reservation Mechanism in Volcano — Evaluation and Decision

**Story:** Choose how a reservation is expressed in Volcano
**Owner:** Apex
**Depends on:** CBGE-222 SUB-13
**Status:** Draft for review
**Blocks:** reservation menu, execution path, showback attribution

## 1. Why this decision is made once

The menu of reservable sizes, the execution path that fulfils a reservation, and the showback attribution that reports on it are all built against whichever mechanism is chosen. Choosing once means building each of them once.

The uncomfortable premise: **Volcano gang-schedules, it does not reserve.** There is no `Reservation` object. Every option below is reserved capacity *expressed* through a scheduling primitive that was designed for something else. The rest of the epic assumes an answer exists; this document produces it.

## 2. What Volcano is, and how it relates to Kubernetes

### 2.1 The gap Volcano fills

The default Kubernetes scheduler places **one Pod at a time**. It has no concept of a job that is only meaningful as a set. Submit a distributed training job needing 8 Pods to a cluster with room for 5, and the default scheduler will happily start 5 of them. Those 5 sit occupying GPUs, waiting for peers that cannot be scheduled, while another job does the same thing with the remaining capacity. Neither ever runs. This is **resource deadlock**, and it is the standard failure mode of batch AI workloads on vanilla Kubernetes.

**Volcano** is a CNCF batch scheduler for Kubernetes, donated by Huawei and derived from `kube-batch`. It runs *alongside* the default scheduler — a Pod opts in via `schedulerName: volcano` — and adds the batch semantics Kubernetes lacks:

- **Gang scheduling (all-or-nothing).** A `PodGroup` declares `minMember: 8`. Volcano either places all 8 or places none, so partial allocations never strand GPUs.
- **Queues.** A `Queue` CRD with `weight`, `deserved` and `capability` fields, giving proportional fair-share between tenants.
- **Job lifecycle.** A `Job` CRD with task roles, retry policies and lifecycle hooks, closer to a batch system than to a Kubernetes `Job`.
- **Pluggable actions and plugins** — `enqueue`, `allocate`, `preempt`, `reclaim`, `backfill`, and plugins such as `gang`, `proportion`, `drf`, `binpack`, `predicates`.

In stack terms:

```
Kubernetes API server        Pods, Nodes, CRDs
  └─ Volcano controller      watches PodGroup / Job / Queue CRDs
  └─ Volcano scheduler       decides placement for Pods with schedulerName: volcano
      └─ Queue               fair-share and quota boundary  <- the reservation lever
          └─ PodGroup        gang boundary (minMember)
              └─ Pods        the actual containers on GPUs
```

### 2.2 The critical limitation this whole document exists to work around

**Volcano gang-schedules; it does not reserve.** There is no `Reservation` CRD, no time-bounded hold, no expiry. Its primitives answer "can these N Pods start together, and is this queue within its share?" — not "hold this capacity for team X from Tuesday to Friday whether or not they use it".

Queue `deserved` is the closest thing, and it is a *fair-share guarantee under contention*, not a withholding. It also accounts resources as **scalars**: `nvidia.com/gpu: 2` means any two GPUs, with no notion of which two or how they are connected. Both gaps are what section 6 and section 7 address.

### 2.3 Comparison with the alternatives

| Scheduler | What it is | Gang scheduling | Native reservation | Fit here |
| --- | --- | --- | --- | --- |
| **kube-scheduler** (default) | Ships with Kubernetes. Pod-at-a-time, ResourceQuota per namespace | No | No. `ResourceQuota` caps consumption but withholds nothing | Insufficient. Deadlocks on multi-GPU jobs |
| **Volcano** | CNCF batch scheduler | Yes, `PodGroup.minMember` | **No** | **Chosen.** Already the platform baseline; gang scheduling is required |
| **Kueue** | Kubernetes SIG-scheduling job queueing controller. Admits Jobs, delegates placement to kube-scheduler | Yes, via admission | No, but `ClusterQueue` borrowing/lending and cohorts are closer to quota-with-guarantee than Volcano's model | Credible alternative, more Kubernetes-idiomatic. Not the baseline; adopting it means re-doing the gang-scheduling work |
| **Apache YuniKorn** | Scheduler from the Hadoop/Spark lineage. Hierarchical queues | Yes | No. Hierarchical queue guarantees, same fair-share semantics as Volcano | Strong hierarchical queue model, but same absence of a reservation primitive. Not the baseline |
| **NVIDIA Run:ai** | Commercial GPU orchestration | Yes | **Yes** — quotas, over-quota, and time-bounded reservations are product features | Solves this document outright, but is a commercial product with an NVIDIA entitlement question, the same one that removed NIM from the serving shortlist |
| **Slurm** | HPC batch scheduler. `scontrol create reservation` with start time and duration | Yes, natively | **Yes**, first-class and time-bounded | The only mature *native* reservation model, but it is not Kubernetes. Adopting it means a second control plane beside the one Apex owns |

Two observations worth carrying into the decision:

1. **No Kubernetes-native scheduler has a true reservation primitive.** This is not a Volcano weakness; it is the state of the ecosystem. Slurm has it because HPC scheduling grew up around allocations; Kubernetes grew up around always-on services.
2. **Switching scheduler does not avoid the problem.** Kueue and YuniKorn would require the same synthesis of queue quota plus expiry controller. Volcano stays because it is already the baseline and gang scheduling is a hard requirement — not because it reserves better.

## 3. Fixed constraints

Corrected against the Infrastructure & Platform Inventory workshop of 2026-08-18 and the NVIDIA L40S product specification.

| Constraint | Value |
| --- | --- |
| Fleet at decision time | **GPU One: one DL380 with 3 × NVIDIA L40S, 48 GB each.** Two DL380a's not yet online |
| Interconnect | **PCIe Gen4 x16. L40S does not support NVLink** (NVIDIA spec: "NVIDIA NVLink Support: No"). No bridge exists for this card |
| **Bridged pair** | **Does not exist on the current fleet, and cannot be added to L40S.** See section 7 |
| MIG | Not supported on L40S. GPU sharing is software-level only |
| Future | H200 upgrade is expected for the third DL380 and *would* introduce NVLink bridging. Not present today |
| Scheduler | Volcano, gang scheduling in use |
| Requirement source | RES-1 request, RES-3 approval, RES-4 start/end dates with expiration, RES-6 reporting, RES-7 showback-ready |
| Ordering | Prototype on GPU One **before** the menu is published |

## 4. Candidates

| ID | Mechanism |
| --- | --- |
| A | **Dedicated queue per reservation.** A Volcano `Queue` created per reservation with a guaranteed deserved/capability allocation, deleted at release |
| B | **Capability adjustment on an existing queue.** The tenant's existing queue has its capability raised for the reservation window and lowered at the end |
| C | **Admission policy at submission.** All queues stay as they are; a webhook refuses work that would encroach on reserved capacity |

## 5. Criteria set

| # | Criterion | Failure it prevents |
| --- | --- | --- |
| K1 | Is reserved capacity genuinely withheld from other queues, or merely deprioritised? | A reservation that is only a priority boost is not a reservation |
| K2 | Does the mechanism survive a scheduler restart? | Reservation silently evaporating on a Volcano pod restart |
| K3 | Is release an action the platform takes, or a state that decays? | Capacity stranded forever because nobody ran the release step |
| K4 | Does gang scheduling still function for the reserved workload? | A reserved multi-pod job that can never gang-schedule inside its own reservation |
| K5 | How many concurrent reservations before queue count is an operational problem? | Queue sprawl, scheduler config churn, unreadable showback |
| K6 | Can it hold a topology-qualified set of GPUs, rather than any N GPUs? | A reservation satisfied by the wrong hardware. See section 7: on L40S there is no bridged pair to hold |
| K7 | Is attribution for showback derivable from the mechanism itself? | Reservation usage that cannot be reported per RES-6 and RES-7 |

## 6. Assessment

| Criterion | A: dedicated queue | B: capability adjustment | C: admission policy |
| --- | --- | --- | --- |
| K1 Genuinely withheld | **Yes.** `deserved`/`capability` on a separate queue holds the allocation away from other queues; proportion plugin will not lend it out beyond the sum of deserved | **Partly.** Raising one queue's capability does not lower anyone else's unless the others are lowered too. Without the matching decrease it is a headroom change, not a withholding | **No.** Capacity is not withheld. Encroaching work is refused at submission; work already running is untouched |
| K2 Survives scheduler restart | **Yes.** Queue is a CRD in etcd, reconstructed on restart | **Yes.** Also CRD state | **Yes** for the policy object, **no** for in-flight intent. A webhook down means an open door, so it fails open unless explicitly configured otherwise |
| K3 Release: action or decay | **Action.** Queue must be deleted or zeroed. Needs a controller or a scheduled job driven by RES-4 end date | **Action.** Capability must be lowered back. Same requirement, plus the risk of forgetting which value to restore | **Action.** Policy must be removed, but the blast radius of forgetting is smaller |
| K4 Gang scheduling intact | **Yes.** PodGroup binds to the reservation queue; gang semantics unchanged inside it | **Yes.** Same queue, same PodGroup behaviour | **Yes**, but the webhook can reject part of a gang's context and interact badly with retry loops |
| K5 Concurrency ceiling | One queue per reservation. Practical on this fleet — three GPUs on one host support at most one 2-GPU reservation alongside a single shared GPU, or three 1-GPU reservations (see 7.3). Queue sprawl is a real problem at fleet scale, not at this scale | No new queues at all. Highest concurrency headroom | No new queues. High headroom |
| K6 Topology | **Not by itself.** Volcano queues account for `nvidia.com/gpu` as a scalar; two GPUs from a queue quota is *any* two. Topology must be expressed as a distinct resource name, node affinity, or a dedicated node — see section 7 | Same limitation, same fix | Same limitation, and the policy would have to encode topology itself |
| K7 Showback attribution | **Best.** Queue name is the reservation identity. Every pod, every metric, every usage record carries it | Weak. Reserved and shared usage flow through the same queue and must be separated by time window and labels | Weak. Nothing in the mechanism records what was reserved, only what was refused |

## 7. The bridged-pair question, answered explicitly

The acceptance criterion asks whether the chosen mechanism can hold a *bridged pair* specifically, rather than any two GPUs. The answer has two parts, and the first one supersedes the second on the current fleet.

### 7.1 There is no bridged pair to hold

**GPU One is fitted with 3 × NVIDIA L40S. The L40S does not support NVLink.** NVIDIA's product specification lists "NVIDIA NVLink Support: No"; there is no NVLink bridge, no SXM variant, and no field-installable option. All inter-GPU traffic goes over PCIe Gen4 x16 at 64 GB/s.

Therefore, on the fleet as it exists today:

- **A "bridged pair" is not a thing that can be reserved, because it is not a thing that exists.** Any two L40S in GPU One are equivalent: same chassis, same PCIe fabric, no privileged pairing.
- The requirement collapses to **"two GPUs on the same host, with PCIe peer-to-peer available"** — which *is* a real and checkable topology constraint, just a much weaker one than NVLink bonding.
- This must be corrected wherever the earlier "bridged pair" phrasing appears. Publishing a reservation menu offering a bridged pair on L40S hardware would be selling something the fleet cannot deliver — precisely the failure the prototype-before-menu ordering exists to prevent.

**The bridged-pair requirement becomes live only when the H200 upgrade lands**, since H200 supports 4-way NVLink bridges. The design below is therefore built so the constraint can be switched on later without re-deciding the mechanism.

### 7.2 Why queue quota alone would still be insufficient

Independent of the hardware fact above, it is worth recording the structural limitation, because it applies to *any* topology constraint including the weaker PCIe-P2P one.

**Volcano queue quota is scalar resource accounting.** A quota of two `nvidia.com/gpu` is satisfied by any two GPUs the scheduler finds, on any node, with any interconnect. Volcano has no topology awareness in queue accounting.

The mechanism must therefore be **queue quota plus a topology constraint**. Options, in preference order:

1. **Distinct extended resource name.** Advertise the topology-qualified GPU set as its own resource (for example `apex.io/gpu-p2p` today, `apex.io/gpu-nvlink` once H200 lands) via device-plugin configuration or node labels plus a resource shim. The queue reserves *that* resource, so quota and topology become the same statement. Cleanest, and the only option where a reservation cannot be accidentally satisfied by the wrong hardware. It is also the option that absorbs the H200 change as a new resource name rather than a new mechanism.
2. **Node affinity plus node label.** Label the node and require the label in the reservation's PodGroup. Works, but topology correctness now depends on the submitted workload spec rather than on the reservation, so a workload that omits the affinity bypasses it.
3. **Dedicated node.** The reservation reserves the whole node. Simple, least flexible, and on a single-node fleet indistinguishable from option 1 in effect.

Option 1 is the proposal. Option 3 is the fallback if device-plugin changes are not permitted on the approved platform stack.

> While the fleet is a single node with three homogeneous PCIe-only L40S, options 1 and 3 are indistinguishable in effect and the topology constraint is close to vacuous. Option 1 is proposed because it is the one that still holds when the second and third nodes arrive and when H200 introduces a genuine NVLink topology. Choosing option 3 instead is acceptable only on the understanding that both fleet growth and the H200 upgrade would force this decision to be re-opened.

### 7.3 The odd-number consequence

Three GPUs on one host is an awkward number for reservations, and it is worth stating before the menu is drafted. A two-GPU reservation leaves a single stranded GPU; two concurrent two-GPU reservations do not fit. The realistic menu on GPU One alone is **one 2-GPU reservation plus one 1-GPU shared slot, or three 1-GPU slots**. Sizing beyond that waits for the DL380a's to come online.

## 8. Recommendation

**Recommendation: A — a dedicated Volcano queue per reservation, with topology expressed as a distinct extended resource (section 7.2, option 1), and release driven by an expiry controller keyed on the RES-4 end date.**

**Reason.** Only A genuinely withholds capacity (K1), and withholding is the definition of a reservation. It is the only option where reservation identity is a first-class object, which makes showback attribution (K7) fall out of the mechanism instead of being reconstructed from timestamps. It survives restart (K2) because it is CRD state, and it leaves gang scheduling untouched (K4). Its known weakness is queue sprawl (K5), which is not a problem on a three-GPU single-node fleet and is a problem to solve at fleet growth, not now.

**Rejections, with reasons:**

- **B, capability adjustment** — raising one queue's capability without lowering others deprioritises rather than withholds, and reserved and shared usage share a queue, so showback has to be reconstructed from labels and windows. It also creates a restore-the-old-value failure mode with no record of what the old value was.
- **C, admission policy** — refuses future encroachment but reclaims nothing already running, so a reservation starting at 09:00 is only honoured if the fleet happened to be idle at 09:00. It is a useful *complement* to A and is retained as a guard against direct submission bypassing the reservation queues, but it is not the mechanism.

**Release model:** an action, not a decay. An expiry controller reconciles reservation end dates and deletes or zeroes the queue. Decay is rejected because there is no TTL primitive on a Volcano queue, and simulating one by leaving capacity to lapse strands GPUs on a fleet that has three.

## 9. Prototype gate — the menu is not published before this passes

Publishing sizes the fleet cannot hold is the failure this ordering avoids. Each row is executed on GPU One and the result recorded before the reservation menu is published.

| # | Test | Pass condition |
| --- | --- | --- |
| P1 | Create a reservation queue holding two of the three L40S | Queue admitted; capacity reflected in Volcano queue status |
| P2 | Submit a workload to the shared queue that would consume the reserved GPUs | Workload stays pending; it does not get the reserved capacity |
| P3 | Submit a gang-scheduled multi-pod job into the reservation queue | Gang schedules and runs |
| P4 | Verify the reservation is satisfied only by the topology-qualified resource, not by any two GPUs | Workload lands on the intended pair; a request for the plain `nvidia.com/gpu` resource does not consume it |
| P4b | Confirm PCIe peer-to-peer is enabled between the L40S cards on the DL380 | `nvidia-smi topo -m` shows P2P-capable links, not `SYS` traversal through host RAM |
| P5 | Restart the Volcano scheduler with the reservation active | Reservation intact after restart; the running reserved workload is undisturbed |
| P6 | Trigger the expiry path at the reservation end date | Queue removed or zeroed; capacity returns to shared; usage record closed |
| P7 | Confirm showback attribution | Reservation usage attributable to the reservation identity, per RES-6 and RES-7 |

## 10. Open items

| # | Item | Resolves when |
| --- | --- | --- |
| O1 | CBGE-222 SUB-13 outcome | Dependency closed |
| O2 | Whether device-plugin changes are permitted for the topology-qualified extended resource | Platform stack approval |
| O2b | Reservation menu sizing given **three** GPUs on one host, not two — see 7.3 | Before menu publication |
| O2c | When the H200 upgrade lands, reinstating a genuine NVLink bridged-pair constraint | HPE infrastructure |
| O3 | Expiry controller: new controller, Argo CronWorkflow, or reservation service responsibility | Design review |
| O4 | Whether the admission webhook is adopted as a complementary guard | After P2 |
| O5 | Queue-count ceiling to publish as an operational limit | After the two DL380a's are online |

## 11. Decision record

| Field | Value |
| --- | --- |
| Decision | Dedicated Volcano queue per reservation, topology expressed as a distinct extended resource, release by expiry controller |
| Date | *to be filled at sign-off* |
| Decider | *named at sign-off* |
| Basis | Section 6 assessment; conditional on the section 9 prototype passing on GPU One |
| Reverses on | Prototype P1-P7 failing; device-plugin change refused, forcing the dedicated-node fallback; fleet growth making queue-per-reservation operationally unworkable; a Volcano release introducing a native reservation primitive |

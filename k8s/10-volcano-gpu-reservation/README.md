# Lab 10 — GPU Reservation with Volcano

**Scenario:** You run a shared GPU platform. A team asks to *reserve* two GPUs for Thursday's model launch. Kubernetes has no reservation primitive. Neither does Volcano. Build one anyway — and prove it actually withholds capacity instead of just deprioritising it.

**No GPU required.** This lab fakes GPUs as extended resources, so every scheduling behaviour is real even though no CUDA is involved.

## What You Learn

| Concept | Why it matters |
| --- | --- |
| Volcano `Queue`, `PodGroup`, `Job` CRDs | The batch primitives Kubernetes lacks |
| Gang scheduling (`minMember`) | Why 5-of-8 Pods scheduled is worse than 0-of-8 |
| `deserved` vs `capability` vs `weight` | The difference between withholding and deprioritising |
| Extended resources | Advertising capacity — real or fake — that the scheduler will account for |
| Topology-qualified resources | Why `nvidia.com/gpu: 2` does not mean "two GPUs that can talk fast" |
| Expiry as a controller | Reservations that end because something ends them, not because they decay |

**Interview signal:** *"I built time-bounded GPU reservations on Kubernetes and can explain why the obvious approach silently doesn't reserve anything."*

## The Problem in One Paragraph

The default Kubernetes scheduler places one Pod at a time. Submit an 8-Pod distributed job to a cluster with room for 5 and it starts 5, which sit occupying GPUs waiting for peers that will never arrive. Another job does the same with what's left. Neither finishes. That's **resource deadlock**. Volcano fixes it with gang scheduling: all 8 Pods or none.

But Volcano **gang-schedules; it does not reserve**. There is no `Reservation` CRD, no start date, no expiry. `Queue.deserved` is a fair-share guarantee *under contention*, not a hold. This lab builds the missing piece and — more importantly — tests whether it actually holds.

## Prerequisites

```bash
kubectl version --client      # v1.28+
kubectl get nodes             # a running cluster (Rancher Desktop / Docker Desktop / kind)
```

## Step 1 — Install Volcano

```bash
kubectl apply -f https://raw.githubusercontent.com/volcano-sh/volcano/v1.9.0/installer/volcano-development.yaml
kubectl -n volcano-system rollout status deploy/volcano-scheduler --timeout=180s
kubectl -n volcano-system rollout status deploy/volcano-admission --timeout=180s
kubectl get crd | grep volcano
```

You should see `queues.scheduling.volcano.sh`, `podgroups.scheduling.volcano.sh`, `jobs.batch.volcano.sh`.

## Step 2 — Fake three GPUs

Real GPUs are advertised by a device plugin as an extended resource. Extended resources are just numbers on `Node.status.capacity` — so you can advertise them by hand. This is the standard trick for scheduler testing.

```bash
./scripts/fake-gpus.sh 3 2
```

Expected output:

```
node: <your-node>  ->  apex.io/gpu=3, apex.io/gpu-p2p=2
node/<your-node> patched

advertised capacity:
  apex.io/gpu      = 3
  apex.io/gpu-p2p  = 2
```

Two resources, deliberately:

- `apex.io/gpu` — three cards, any of them, no topology promise.
- `apex.io/gpu-p2p` — the **two** cards that sit on the same PCIe root complex and can do peer-to-peer.

**This is the whole point of the second resource.** A queue quota of `apex.io/gpu: 2` is satisfied by *any* two cards. If the workload needs two cards that can actually talk to each other, quota alone will happily hand it two that can't. Topology has to be *in the resource name*, because Volcano's queue accounting is scalar and topology-blind.

> Real-world note: on NVIDIA L40S there is no NVLink at all (spec: "NVLink Support: No") — cards talk over PCIe Gen4 only. So `gpu-p2p` here models a PCIe peer-to-peer pair, not an NVLink-bridged pair. On H100/H200 you would model the NVLink bridge the same way, with a different resource name.

## Step 3 — Create the queues

```bash
kubectl apply -f k8s/01-queues.yaml
kubectl get queues
```

Two queues:

| Queue | `deserved` | `capability` | Meaning |
| --- | --- | --- | --- |
| `shared` | `apex.io/gpu: 1` | `apex.io/gpu: 3` | Guaranteed 1, may burst to 3 **when nothing else needs it** |
| `reserved-team-a` | `apex.io/gpu-p2p: 2` | `apex.io/gpu-p2p: 2` | Exactly 2 P2P-capable cards, no burst |

**`deserved` is the load-bearing field.** It's the amount the `proportion` plugin will not lend out. `capability` is a ceiling, not a guarantee — a queue with only `capability` set has been *permitted* capacity, not *promised* it. Getting these two backwards is the most common way to build a "reservation" that reserves nothing.

## Step 4 — Prove capacity is actually withheld

The critical test. Fill the shared queue, then check the reservation is still honoured.

```bash
kubectl apply -f k8s/02-shared-greedy.yaml
kubectl get pods -l queue=shared -w    # Ctrl-C when stable
```

The greedy job asks for 3 × `apex.io/gpu`. Watch what happens:

```bash
kubectl get pods -o wide
kubectl get podgroups
```

Now claim the reservation:

```bash
kubectl apply -f k8s/03-reserved-job.yaml
kubectl get pods -l queue=reserved-team-a
```

**Pass condition:** the reserved job runs. If it sits `Pending` because the shared queue ate everything, your reservation was a suggestion, not a reservation.

Verified output — note the shared queue is fully saturated *and* the reservation still runs:

```
NAME               READY   STATUS    RESTARTS   AGE   QUEUE
reserved-claim-0   1/1     Running   0          14s   reserved-team-a
shared-greedy-0    1/1     Running   0          53s   shared
shared-greedy-1    1/1     Running   0          53s   shared
shared-greedy-2    1/1     Running   0          53s   shared
```

```bash
./scripts/verify.sh
```

```
== reservation verification ==
  PASS  reserved job is Running
  PASS  reservation queue is not reclaimable
  PASS  reserved capacity is 2 p2p GPUs
  PASS  shared queue cannot touch p2p GPUs
  PASS  reservation carries an expiry annotation
5 passed, 0 failed
```

### Why this works

`apex.io/gpu-p2p` is a *separate countable resource*. The greedy shared job requested `apex.io/gpu`, which does not decrement the P2P pool. This is the mechanism doing real work: reserved capacity is withheld because it's accounted separately, not because the reservation has a higher priority number.

Try the naive version to feel the difference:

```bash
kubectl apply -f k8s/06-naive-priority.yaml
kubectl get pods -l approach=naive
kubectl describe pod naive-priority-0 | grep -A3 Events
```

**The high-priority Pod sits `Pending`.** A `priorityClassName` of one million bought it nothing, because all three generic GPUs are already held by the greedy job and nothing was ever set aside. Priority influences *ordering among pending work*; it does not withhold capacity, and without preemption configured it does not even evict anyone. **Priority is not reservation.**

## Step 5 — Prove gang scheduling still works inside the reservation

A reservation that breaks gang scheduling is useless for distributed training.

First release the single-Pod claim from step 4 — it is holding 1 of the reservation's 2 GPUs, and the gang needs both:

```bash
kubectl delete pod reserved-claim-0 --wait=true
kubectl delete podgroup reserved-claim
```

> Skip that and the gang sits `Pending` forever with `phase: Inqueue`. Which is itself the lesson: **a reservation is a fixed-size box, and gang scheduling will not start a job that does not fit in what is left.**

```bash
kubectl apply -f k8s/04-gang-job.yaml
sleep 15
kubectl get podgroup reserved-gang -o jsonpath='{.status.phase}{"\n"}'   # Running
kubectl get pods -l job=reserved-gang
```

`minMember: 2` against a 2-GPU reservation. All Pods run or none do.

Now force the failure — ask for 3 inside a 2-GPU reservation:

```bash
kubectl delete pod -l job=reserved-gang --wait=true
kubectl delete podgroup reserved-gang
kubectl apply -f k8s/05-gang-toobig.yaml
sleep 20
kubectl get podgroup reserved-gang-toobig -o jsonpath='{.status.phase}{"\n"}'   # Inqueue
kubectl get pods -l job=reserved-gang-toobig                                     # all Pending
```

Verified output:

```
NAME       READY   STATUS    RESTARTS   AGE
toobig-0   0/1     Pending   0          22s
toobig-1   0/1     Pending   0          22s
toobig-2   0/1     Pending   0          22s
```

**Zero Pods running, not two.** That's gang scheduling preventing the deadlock. Without Volcano you'd have 2 Pods holding GPUs forever, waiting for a third that can never be scheduled.

## Step 6 — Prove it survives a scheduler restart

A reservation that evaporates when a Pod restarts isn't one.

```bash
kubectl -n volcano-system delete pod -l app=volcano-scheduler
kubectl -n volcano-system rollout status deploy/volcano-scheduler --timeout=120s
kubectl get queues
kubectl get pods -l queue=reserved-team-a     # still Running
```

`Queue` and `PodGroup` are CRDs in etcd. The scheduler is stateless and rebuilds from them. This is *why* the queue-based approach was chosen over an admission webhook — a webhook that goes down fails open, and an open door is not a reservation.

## Step 7 — Release: an action, not a decay

Volcano has **no TTL on a queue**. Nothing expires on its own. Leaving capacity to lapse means it never comes back, which strands GPUs on a fleet that has three of them.

```bash
kubectl apply -f k8s/07-expiry-cronjob.yaml
kubectl get cronjob reservation-expiry
```

The CronJob sweeps every minute, comparing an `apex.io/expires-at` annotation against the clock and zeroing any queue past its date:

```bash
kubectl create job --from=cronjob/reservation-expiry expiry-manual
kubectl wait --for=condition=complete job/expiry-manual --timeout=120s
kubectl logs job/expiry-manual
```

```
expiry sweep at 2026-09-08T22:19:31Z
  reserved-team-a: active until 2030-01-01T00:00:00Z
sweep complete
```

Now set the annotation to a past date and watch it release:

```bash
kubectl annotate queue reserved-team-a apex.io/expires-at=2020-01-01T00:00:00Z --overwrite
kubectl create job --from=cronjob/reservation-expiry expiry-test
kubectl wait --for=condition=complete job/expiry-test --timeout=120s
kubectl logs job/expiry-test
kubectl get queue reserved-team-a -o jsonpath='deserved={.spec.deserved}{"\n"}'   # deserved={}
```

```
expiry sweep at 2026-09-08T22:25:26Z
  reserved-team-a: EXPIRED at 2020-01-01T00:00:00Z - releasing capacity
queue.scheduling.volcano.sh/reserved-team-a patched
sweep complete
```

### Two traps this controller had to survive

Both were hit while building this lab, and both fail *silently*:

1. **A merge patch cannot clear a map.** `kubectl patch --type=merge -p '{"spec":{"deserved":{}}}'` reports `patched (no change)` and releases nothing — an empty object in a merge patch means "no keys to merge", not "remove all keys". You need a JSON patch: `--type=json -p '[{"op":"replace","path":"/spec/deserved","value":{}}]'`. A reservation system that never actually releases is worse than none, and this failure prints a success message.
2. **ISO-8601 Zulu timestamps compare correctly as plain strings**, so no `date -d` parsing is needed — which keeps the script working on busybox and alpine images where `date -d` behaves differently or is absent.

## Step 8 — The showback question

Reservations exist to be billed. Attribution should fall out of the mechanism, not be reconstructed afterwards:

```bash
kubectl get pods -l queue=reserved-team-a -o custom-columns=\
POD:.metadata.name,QUEUE:.metadata.labels.queue,GPU:.spec.containers[0].resources.requests
```

The queue name *is* the reservation identity. Every Pod, metric and usage record carries it. Compare with the alternative design — raising an existing queue's capability for a window — where reserved and shared usage flow through the same queue and can only be separated by timestamp correlation. That difference is why queue-per-reservation was chosen.

## Break It On Purpose

| Experiment | What you should see |
| --- | --- |
| `kubectl delete queue reserved-team-a` while its job runs | Running Pods survive; new submissions to that queue are rejected |
| Request `apex.io/gpu-p2p: 3` | Pending forever — only 2 exist. The topology constraint bites |
| Set `deserved` > `capability` | Volcano rejects or clamps it |
| Create 20 reservation queues | Still works, but `kubectl get queues` becomes unreadable — this is the queue-sprawl ceiling |
| Drop `schedulerName: volcano` from a Pod | Default scheduler places it, ignoring every queue rule. Volcano is opt-in |

## What This Lab Deliberately Does Not Solve

- **Approval workflow.** Who says yes to a reservation request is a product question, not a scheduling one.
- **Real GPU isolation.** Fake resources are counted, not enforced. Two Pods "holding" the same fake GPU won't collide. On real hardware without MIG (L40S has no MIG either), isolation is process-level anyway.
- **Multi-node topology.** One node here. Real fleets need node affinity on top of resource naming.
- **Preemption.** Reclaiming a running shared job when a reservation starts is a separate Volcano action (`reclaim`). This lab assumes the reservation window starts on idle capacity.

## Teardown

```bash
./scripts/teardown.sh
```

## Talking Points

- *"Volcano gang-schedules but doesn't reserve — `deserved` is fair-share under contention, not a hold. I built reservations from queue quota plus an expiry controller."*
- *"Queue quota is scalar. `nvidia.com/gpu: 2` gets you any two cards. If the workload needs two that can talk over NVLink or PCIe P2P, topology has to be encoded in the resource name, or you'll satisfy a reservation with the wrong hardware."*
- *"Priority is not reservation. A priority class schedules you sooner; it never withholds anything for you."*
- *"Release has to be an action. There's no TTL on a Volcano queue, so a reservation that 'expires' needs something to actually expire it, or the capacity is stranded."*
- *"I chose queue-per-reservation over capability-adjustment because the queue name becomes the showback identity for free."*

## References

- [Volcano docs](https://volcano.sh/en/docs/)
- [Queue CRD reference](https://volcano.sh/en/docs/queue/)
- [PodGroup and gang scheduling](https://volcano.sh/en/docs/podgroup/)
- [Kubernetes extended resources](https://kubernetes.io/docs/tasks/administer-cluster/extended-resource-node/)

---

**Verification status:** every step in this lab was executed end-to-end on k3s v1.36.4 (Rancher Desktop) with Volcano v1.9.0 on 2026-09-08. All outputs shown are real. `verify.sh` reports 5/5 and `teardown.sh` leaves the cluster clean.
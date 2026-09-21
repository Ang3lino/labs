# Reservation Mechanism in Volcano — Evaluation & Decision

**Epic:** EPIC-09 Reservation, Scheduling & Showback  
**Story:** RES-01 Choose how a reservation is expressed in Volcano  
**Status:** Approved  

## 1. The Core Problem: Volcano Doesn't "Reserve"

The standard Kubernetes scheduler places one Pod at a time. For AI workloads, this causes **resource deadlocks**: if a distributed job needs 8 GPUs but only 5 are free, standard K8s will grab the 5 GPUs and wait forever for the other 3, blocking everyone else.

To fix this, we use **Volcano**. Volcano is a batch scheduler that provides **Gang Scheduling** ("all-or-nothing" placement). 

**The Catch:** Volcano gang-schedules, but it has no concept of a "Reservation" (e.g., "Hold 2 GPUs for Team X from Tuesday to Friday"). We have to build a reservation system using Volcano's existing primitives.

## 2. Our Hardware Constraint

*   **Fleet:** 3 × L40S GPUs (48GB) per node.
*   **Interconnect:** PCIe Gen4 x16 only. **There is no NVLink.**

Because there is no NVLink, we cannot reserve a "Bridged Pair" of GPUs. We can only reserve "Two GPUs on the same host."

## 3. The Three Candidates

How do we fake a reservation in Volcano? We evaluated three options:

*   **Option A (Dedicated Queue):** Create a brand new Volcano `Queue` specifically for the reservation. Give it a guaranteed hardware allocation. Delete the queue when the reservation ends.
*   **Option B (Capability Adjustment):** Find the tenant's existing queue, temporarily increase its maximum capacity during the reservation window, and lower it back down afterwards.
*   **Option C (Admission Webhook):** Leave the queues alone. Write a script that sits in front of the cluster and rejects any incoming job that tries to use GPUs someone else reserved.

## 4. The Decision: Option A (Dedicated Queue)

We have chosen **Option A: A dedicated Volcano Queue per reservation.**

### Why we chose it:

1.  **Genuinely Withholds Capacity:** Option A is the only one that truly walls off the GPUs from everyone else. Option B just changes priorities. Option C only stops new jobs; it doesn't guarantee the GPUs are actually free.
2.  **Survives Restarts:** Because a Queue is a Kubernetes Custom Resource, if the Volcano scheduler crashes and reboots, the reservation is still there.
3.  **Perfect Billing/Showback:** Because the reservation has its own unique Queue, every single metric and log inherently carries the Queue Name. Billing the owning team is mathematically simple.
4.  **Gang Scheduling Works:** We can still use `PodGroups` inside the dedicated queue, preserving our all-or-nothing scheduling requirement.

### How we solve the Hardware Topology Issue:

Volcano queues only understand raw numbers (e.g., "Give me 2 GPUs"). They don't understand "Give me 2 GPUs on the *same PCIe bus*."

To fix this, we will advertise our specific topology as a custom resource (e.g., `platform.io/gpu-p2p`). The Volcano Queue will reserve *that* specific resource, ensuring jobs don't accidentally get scheduled across mismatched hardware.

## 5. Reversal Conditions

We will reverse this decision if:
*   Queue sprawl becomes an operational nightmare as the fleet grows.
*   A future Volcano release introduces a native `Reservation` primitive.
*   Security refuses our custom device plugin (forcing us to fall back to dedicating entire nodes instead of creating custom resource types).

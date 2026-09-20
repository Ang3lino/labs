# EPIC-09: Reservation, Scheduling & Showback

## Story: RES-01 Choose how a reservation is expressed in Volcano

**As the** platform team,  
**I want** one mechanism selected on evidence,  
**So that** the menu, the execution path, and the showback attribution are all built once against the same mechanism.

### Acceptance Criteria

- **Candidate Assessment:** Assess the three primary candidates against a written criteria set and choose one:
  1. A dedicated queue per reservation.
  2. A capability adjustment on an existing queue for the duration of the reservation.
  3. An admission policy at submission that refuses work encroaching on reserved capacity.
- **Criteria Coverage:** At a minimum, the evaluation must answer:
  - Is reserved capacity genuinely withheld from other queues, or merely deprioritized?
  - Does the mechanism survive a scheduler restart?
  - Is release an action the platform takes, or a state that decays?
  - Does gang scheduling still function for the reserved workload?
  - How many concurrent reservations does the mechanism support before queue count becomes an operational problem?
- **Hardware Topology constraint:** Explicitly answer whether the chosen mechanism can hold a specifically connected pair of GPUs (e.g., PCIe peer-to-peer or NVLink bridged), rather than just *any* two GPUs. (A reservation satisfied by two unconnected cards is not a true reservation of a connected pair).
- **Prototype Gate:** The mechanism must be prototyped on the hardware before the reservation menu is published, avoiding the failure of offering sizes the fleet cannot hold.
- **Final Deliverable:** A written decision with a date, a named decider, and specific conditions that would reverse the decision.

### Metadata

- **Depends on:** CBGE-222, SUB-13
- **Proposed Owner:** Platform Team

> **Note:** This is the foundational story the rest of the epic rests on. Volcano *gang-schedules*; it does not natively *reserve*. Everything else in this epic assumes we have figured out a way to force Volcano to act like a reservation system.

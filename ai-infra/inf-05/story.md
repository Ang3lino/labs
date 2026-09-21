# EPIC-05: Inference Serving

## Story: INF-05 Consume the registry contract, and refuse artifacts that do not carry it

**As the** serving layer,  
**I want** the eleven contract fields present on a promoted artifact,  
**So that** a promotion becomes a deployment without anyone being told the missing values by hand.

### Acceptance Criteria

- **Contract Consumption:** Serving must read all required fields from MLflow:
  - Runtime and version
  - Quantization and precision
  - Declared tensor-parallel degree
  - Accelerator requirement or exclusion
  - Maximum context and evaluated concurrency
  - Preprocessing and tokenizer
  - Resource profile
  - Artifact digest
  - Promotion state
  - Owning team
- **Strict Validation:** A deployment attempt against an artifact missing *any* serving-consumed field must fail with an error naming the specific missing field, rather than falling back to a default value.
- **Promotion Gating:** The promotion state must gate deployment; an unpromoted artifact cannot reach the Production environment.
- **Hardware Constraint Enforcement:** A declared tensor-parallel degree above 2 must be rejected at deployment time with a message specifically naming the fleet ceiling.
- **Attribution Propagation:** The "owning team" field must be carried through to the gateway's attribution and to all metric labels (this is the field the consumption dashboard depends on).
- **Cross-Epic Alignment:** Any gaps between this required contract and what MLflow actually holds today must be formally raised with the training pipeline epic as a documented list, not merely as a conversation.

### Metadata

- **Depends on:** INF-01
- **Proposed Owner:** Platform Team (with the training pipeline owner)

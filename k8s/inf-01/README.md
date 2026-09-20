EPIC-05 Inference Serving

INF-01 Evaluate and select the serving runtime 

As the platform team, I want one runtime chosen on evidence across vLLM, NVIDIA NIM, Triton Inference Server and TensorRT-LLM, so that every downstream decision — engine flags, metric names, batching, packaging — is made once against a known target.

Acceptance criteria
- All four candidates assessed against a written criteria set covering, at minimum: tensor-parallel support at a maximum degree of 2; continuous or dynamic batching; token streaming; OpenAI-compatible request surface, or the adapter cost of providing one; native Prometheus metrics including TTFT, queue depth and KV cache utilization; Ray Serve integration; support for the non-LLM forecasting class, which needs no tensor parallelism at all; and licensing and entitlement, since NIM carries an NVIDIA entitlement question that the others do not
- Explicitly recorded: whether each candidate serves both workload classes, or whether the platform ends up running two runtimes — that is an acceptable outcome, but it must be a decision rather than a discovery
- Assessment done at the two-GPU ceiling as a fixed constraint, not as a variable
- Approved-software status of each candidate and its dependencies checked before the recommendation, not after
- A written recommendation with the reason, the version proposed for pinning, and what would reverse it
- Existing documents assume vLLM; if the recommendation is vLLM, the reasoning is still written down rather than inherited

Depends on: nothing (no other story)
Proposed owner: Apex
Note: Evaluating four runtimes properly against unbuilt hardware is not possible before mid-October. The realistic shape is a paper assessment against the criteria above, plus hands-on time with the leading two once GPU One is reachable. Say which parts are measured and which are read.


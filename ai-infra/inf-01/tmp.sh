
labs/ai-infra/inf-01 main  › kubectl port-forward svc/vllm-poc-svc 8000:8000
Forwarding from 127.0.0.1:8000 -> 8000
Forwarding from [::1]:8000 -> 8000


Handling connection for 8000
E0920 20:31:20.108318   55801 portforward.go:424] "Unhandled Error" err=<
	an error occurred forwarding 8000 -> 8000: error forwarding port 8000 to pod c3b7e53a87b8db12ef76e8e2446435c703e7d53055cd379654778cf488c40220, uid : exit status 1: 2026/09/20 20:31:20 socat[11303] W connect(5, AF=2 127.0.0.1:8000, 16): Connection refused
	2026/09/20 20:31:20 socat[11303] E TCP4:localhost:8000: Connection refused
 >
error: lost connection to pod
zsh: exit 1     kubectl port-forward svc/vllm-poc-svc 8000:8000


---

labs/ai-infra/inf-01 main  › scripts/test-openai-surface.sh localhost:8000
=== Testing Models Endpoint ===

=== Testing Chat Completions (Non-Streaming) ===

=== Testing Chat Completions (Streaming) ===
zsh: exit 7     scripts/test-openai-surface.sh localhost:8000

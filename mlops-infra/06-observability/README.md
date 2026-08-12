# Lab 06 — Observability (Prometheus + Grafana)

## Summary

Monitor your ML platform with production-grade observability: Prometheus scrapes metrics (GPU utilization, tokens/sec, latency P99), Grafana visualizes them in real-time dashboards, and alerting notifies you before users notice problems.

## Problem It Solves

Your vLLM service is running. Users complain it's "slow sometimes." Without observability:
- "Is it slow right now?" → you don't know
- "Which GPU is overloaded?" → no visibility
- "When did latency spike?" → no historical data
- "Is the problem the model, the network, or the GPU?" → guessing
- "Are we about to run out of GPU memory?" → find out when it OOMs

Observability answers: **what's happening, where, since when, and why** — in real-time, with history.

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Stack                            │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ vLLM        │  │ GPU (DCGM)  │  │ K8s         │            │
│  │ /metrics    │  │ /metrics    │  │ /metrics    │            │
│  │             │  │             │  │ (kubelet)   │            │
│  │ tokens/sec  │  │ utilization │  │ pod CPU/mem │            │
│  │ latency     │  │ memory      │  │ restarts    │            │
│  │ queue depth │  │ temperature │  │ node status │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                 │                 │                    │
│         └────────────────┼────────────────┘                    │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Prometheus (scraper + time-series DB)                 │      │
│  │                                                       │      │
│  │ Every 15s: GET /metrics from each target              │      │
│  │ Store: metric_name{labels} value timestamp            │      │
│  │ Query: PromQL (powerful query language)               │      │
│  │ Alert: rules trigger when conditions are met          │      │
│  └───────────────────────┬──────────────────────────────┘      │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Grafana (visualization)                               │      │
│  │                                                       │      │
│  │ Dashboards: line charts, gauges, heatmaps, tables     │      │
│  │ Alerts: Slack/PagerDuty/email when thresholds breach  │      │
│  │ Variables: filter by namespace, pod, GPU, model        │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Alertmanager (routing)                                │      │
│  │                                                       │      │
│  │ "GPU temp > 85°C for 5m" → PagerDuty                 │      │
│  │ "vLLM queue > 20 for 2m" → Slack #ml-ops             │      │
│  │ "Pod restart > 3 in 10m" → Slack #incidents           │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

**The pull model (how Prometheus works):**

```
Traditional monitoring (push):
  App → pushes metrics → monitoring server
  Problem: server doesn't know if app is dead or just quiet

Prometheus (pull):
  Prometheus → scrapes /metrics endpoint from apps every 15s
  If scrape fails → Prometheus knows the target is down immediately
  Apps just expose an HTTP endpoint — no client SDK needed
```

**Metrics format (OpenMetrics/Prometheus exposition):**
```
# HELP vllm_request_latency_seconds Request latency in seconds
# TYPE vllm_request_latency_seconds histogram
vllm_request_latency_seconds_bucket{model="phi3",le="0.1"} 45
vllm_request_latency_seconds_bucket{model="phi3",le="0.5"} 123
vllm_request_latency_seconds_bucket{model="phi3",le="1.0"} 156
vllm_request_latency_seconds_sum{model="phi3"} 89.4
vllm_request_latency_seconds_count{model="phi3"} 160

# HELP vllm_tokens_per_second Current generation speed
# TYPE vllm_tokens_per_second gauge
vllm_tokens_per_second{model="phi3"} 142.5
```

**PromQL (the query language):**
```promql
# Average tokens/sec over last 5 minutes
rate(vllm_prompt_tokens_total[5m])

# P99 latency
histogram_quantile(0.99, rate(vllm_request_latency_seconds_bucket[5m]))

# GPU utilization across all GPUs
avg(DCGM_FI_DEV_GPU_UTIL)

# GPU memory usage as percentage
DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_FREE * 100

# Alert: queue too deep
vllm_num_requests_waiting > 10
```

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **Prometheus + Grafana** | K8s-native, free, industry standard. Most common stack. | Managed/serverless where vendor tools are free (CloudWatch, Datadog) |
| **Victoria Metrics** | Drop-in Prometheus replacement with better performance + long-term storage | When Prometheus is sufficient (VM is more complex to operate) |
| **Datadog** | Managed, beautiful UI, traces + logs + metrics unified. Enterprise. | Cost-sensitive (expensive at scale), on-prem requirement |
| **CloudWatch** | AWS-native, zero setup on AWS services | Multi-cloud, on-prem, K8s-native workflows |
| **Elastic (ELK)** | Logs + search (not metrics-first) | Pure metrics monitoring (Prometheus is better) |
| **W&B** | ML experiment tracking (training curves) | Infrastructure monitoring (not its purpose) |

**Decision rule**: On K8s → Prometheus + Grafana. Period. It's the CNCF standard. Victoria Metrics if you need better long-term retention.

## Industry Scenarios

| Company / Pattern | Observability Stack |
|---|---|
| **HPE AI Platform** (your project) | Grafana + Victoria Metrics + DCGM Exporter. Dashboards per platform tier, per consumer. |
| **Spotify** | Prometheus + Grafana on GKE. 500+ dashboards. |
| **Uber** | M3 (custom Prometheus-compatible) + Grafana |
| **Any K8s shop** | kube-prometheus-stack Helm chart (Prometheus + Grafana + Alertmanager + node-exporter) |
| **ML platform SLOs** | "P99 latency < 2s, tokens/sec > 100, GPU util > 60%" — all measured via Prometheus |

## Key Terms

- `Prometheus` — pull-based time-series database + alerting engine
- `Grafana` — visualization platform (dashboards)
- `PromQL` — Prometheus query language
- `Scrape` — Prometheus pulling /metrics from a target
- `ServiceMonitor` — K8s CRD telling Prometheus what to scrape
- `Alertmanager` — routes fired alerts to Slack/PagerDuty/email
- `DCGM Exporter` — exposes GPU metrics as Prometheus metrics
- `kube-prometheus-stack` — Helm chart bundling the full stack
- `SLO (Service Level Objective)` — target: "99.9% of requests < 2s"
- `SLI (Service Level Indicator)` — the metric measuring the SLO
- `Histogram` — distribution of values (for percentiles)
- `Gauge` — current value (temperature, queue depth)
- `Counter` — monotonically increasing (total requests)
- `rate()` — per-second rate of a counter increase
- `histogram_quantile()` — compute percentiles from histogram

## Interview Talking Points

"I built the observability layer for our ML serving platform using kube-prometheus-stack. DCGM Exporter feeds GPU metrics — utilization, memory, temperature — into Prometheus. vLLM exposes inference metrics natively: tokens/sec, queue depth, P50/P99 latency. I built Grafana dashboards sliced by model, namespace, and consumer team. Our SLOs are P99 latency < 2s and GPU utilization > 60%; Alertmanager fires to Slack when we breach. We use Victoria Metrics for 90-day retention of historical metrics to track capacity planning trends."

## Exercises

### Exercise 1: Install kube-prometheus-stack

```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install full stack (Prometheus + Grafana + Alertmanager + node-exporter)
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword=admin

# Access Grafana
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
# Open http://localhost:3000 (admin/admin)

# Access Prometheus
kubectl port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090 -n monitoring
# Open http://localhost:9090
```

### Exercise 2: Explore built-in dashboards

Once Grafana is open:
1. Go to Dashboards → Browse
2. Open "Kubernetes / Compute Resources / Namespace (Pods)"
3. Select namespace `ml-serving`
4. See CPU, memory, network per pod — out of the box

### Exercise 3: Query Prometheus directly

Open Prometheus UI (localhost:9090) and try:

```promql
# All pods' CPU usage
sum(rate(container_cpu_usage_seconds_total{namespace="ml-serving"}[5m])) by (pod)

# Memory usage in MB
container_memory_working_set_bytes{namespace="ml-serving"} / 1024 / 1024

# Pod restarts (detect crash loops)
kube_pod_container_status_restarts_total{namespace="ml-serving"}

# Node CPU capacity vs usage
1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)
```

### Exercise 4: Add GPU metrics (DCGM)

```bash
# GPU Operator already installs DCGM Exporter (from Lab 03)
# Create a ServiceMonitor to tell Prometheus to scrape it

kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: dcgm-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: nvidia-dcgm-exporter
  namespaceSelector:
    matchNames: [gpu-operator]
  endpoints:
  - port: metrics
    interval: 15s
EOF
```

Now query GPU metrics in Prometheus:
```promql
# GPU utilization (%)
DCGM_FI_DEV_GPU_UTIL

# GPU memory used (bytes)
DCGM_FI_DEV_FB_USED * 1024 * 1024

# GPU temperature
DCGM_FI_DEV_GPU_TEMP
```

### Exercise 5: Monitor vLLM inference metrics

vLLM exposes Prometheus metrics natively on `/metrics`:

```bash
# Create ServiceMonitor for vLLM
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm-phi3
  namespaceSelector:
    matchNames: [ml-serving]
  endpoints:
  - port: "8000"
    path: /metrics
    interval: 15s
EOF
```

Key vLLM metrics to query:
```promql
# Generation throughput (tokens/sec)
rate(vllm_generation_tokens_total[1m])

# Requests waiting in queue
vllm_num_requests_waiting

# Request latency P95
histogram_quantile(0.95, rate(vllm_e2e_request_latency_seconds_bucket[5m]))

# KV-cache utilization
vllm_gpu_cache_usage_perc
```

### Exercise 6: Build a custom ML dashboard in Grafana

Create a new dashboard with these panels:

| Panel | Query | Visualization |
|---|---|---|
| Tokens/sec | `rate(vllm_generation_tokens_total[1m])` | Time series |
| Request Latency P50/P95/P99 | `histogram_quantile(0.5/0.95/0.99, ...)` | Time series (3 lines) |
| GPU Utilization | `DCGM_FI_DEV_GPU_UTIL` | Gauge (0-100%) |
| GPU Memory | `DCGM_FI_DEV_FB_USED` | Bar gauge |
| Queue Depth | `vllm_num_requests_waiting` | Stat |
| Requests/min | `rate(vllm_request_success_total[1m]) * 60` | Time series |

### Exercise 7: Set up alerts

```yaml
# alert-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: ml-serving-alerts
  namespace: monitoring
spec:
  groups:
  - name: ml-serving
    rules:
    - alert: HighLatency
      expr: histogram_quantile(0.99, rate(vllm_e2e_request_latency_seconds_bucket[5m])) > 5
      for: 2m
      labels:
        severity: warning
      annotations:
        summary: "vLLM P99 latency > 5s for 2 minutes"
    
    - alert: GPUOverheating
      expr: DCGM_FI_DEV_GPU_TEMP > 85
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "GPU temperature > 85°C for 5 minutes"
    
    - alert: QueueBacklog
      expr: vllm_num_requests_waiting > 20
      for: 1m
      labels:
        severity: warning
      annotations:
        summary: "vLLM queue depth > 20 — consider scaling up"
    
    - alert: LowGPUUtilization
      expr: avg(DCGM_FI_DEV_GPU_UTIL) < 10
      for: 30m
      labels:
        severity: info
      annotations:
        summary: "GPU utilization < 10% for 30 min — scale down?"
```

```bash
kubectl apply -f alert-rules.yaml
# Check in Prometheus UI → Alerts tab
```

### Exercise 8: SLO definition and tracking

```promql
# Define SLO: 99.5% of requests complete in < 2 seconds

# SLI (the measurement):
sum(rate(vllm_e2e_request_latency_seconds_bucket{le="2.0"}[1h]))
/
sum(rate(vllm_e2e_request_latency_seconds_count[1h]))

# If this drops below 0.995 → SLO violated

# Error budget remaining (how much failure budget is left this month):
1 - (
  (1 - (sum(rate(vllm_e2e_request_latency_seconds_bucket{le="2.0"}[30d])) / sum(rate(vllm_e2e_request_latency_seconds_count[30d]))))
  / (1 - 0.995)
)
```

## References

- [Prometheus documentation](https://prometheus.io/docs/)
- [Grafana documentation](https://grafana.com/docs/grafana/latest/)
- [PromQL cheat sheet](https://promlabs.com/promql-cheat-sheet/)
- [kube-prometheus-stack Helm chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [DCGM Exporter metrics list](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html)
- [Google SRE Book — Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [vLLM metrics documentation](https://docs.vllm.ai/en/latest/serving/metrics.html)

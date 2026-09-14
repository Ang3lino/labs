# Kubernetes — Learning Guide

> What tripped me up, explained so it doesn't again.

## Cluster Architecture (mental model)

```
Cluster
├── Node 1 (machine — CPU, RAM, disk)
│   ├── Pod A (your app containers)
│   └── Pod B
├── Node 2 (machine)
│   └── Pod C
└── Control Plane
    ├── API Server      ← kubectl talks to this
    ├── Scheduler       ← decides which node gets which pod
    ├── etcd            ← stores all cluster state
    └── Controller Mgr  ← ensures desired state = actual state
```

**Node** = a machine. **Pod** = containers running on a node. Pods are ephemeral (die and get replaced). Nodes are relatively permanent.

## Imperative vs Declarative

| | Imperative | Declarative |
|---|---|---|
| How | `kubectl run/create/set/expose` | `kubectl apply -f file.yaml` |
| Analogy | "Make me a pizza" | "Here's the recipe, match it" |
| Exam use | Fast one-offs | When you need to edit YAML |

## kubectl explain — the exam cheat code

`explain` is a built-in docs lookup. You don't memorize YAML — you look it up.

```bash
# Start at the root
kubectl explain pod                              # top-level: metadata, spec, status

# Drill with dots
kubectl explain pod.spec                         # containers, volumes, tolerations...
kubectl explain pod.spec.tolerations             # key, operator, value, effect

# Dump entire tree
kubectl explain pod.spec.volumes.projected --recursive

# Find a field you don't know the path to
kubectl explain pod --recursive | grep -i toleration
kubectl explain pod --recursive | grep -B 5 -i toleration   # show parents above match

# Works for any resource
kubectl explain deployment.spec.template.spec
kubectl explain service.spec
```

**Discovery flow:**
1. `explain <resource>` → see top-level sections
2. `explain <resource>.<section>` → drill deeper
3. `--recursive | grep -i <keyword>` → find anything you can't guess
4. Each field's description tells you if it's required, its default, etc.

## Generating YAML (never write from scratch)

```bash
kubectl run nginx --image=nginx --dry-run=client -o yaml > pod.yaml
kubectl create deploy web --image=nginx --dry-run=client -o yaml > dep.yaml
```

Edit the skeleton. Faster and fewer indent mistakes.

**Tip**: delete `status: {}` from generated YAML — it's noise and causes indent traps.

## ServiceAccounts vs User Accounts

| | ServiceAccount | User Account |
|---|---|---|
| **What** | Identity for **pods/processes** inside the cluster | Identity for **humans** outside the cluster |
| **Managed by** | Kubernetes (`ServiceAccount` object) | External (certs, OIDC, cloud IAM) |
| **Created how** | `kubectl create sa my-sa` | Not a K8s object — lives in kubeconfig / identity provider |
| **Namespaced** | Yes | No — cluster-wide |

**Key insight**: K8s has no "User" API object. Your `kubectl` identity comes from `~/.kube/config`. ServiceAccounts are first-class K8s objects that pods use.

### Token mount

Every pod gets a JWT token mounted at `/var/run/secrets/kubernetes.io/serviceaccount/token`. The pod uses it to talk to the API server.

### Disable automount (security)

If the pod doesn't need API access, the token is an attack surface:

```bash
kubectl patch sa dashboard-sa -p '{"automountServiceAccountToken": false}'
```

### Manual token injection (projected volume)

When automount is off but you need the token:

```yaml
spec:
  serviceAccountName: dashboard-sa
  automountServiceAccountToken: false
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
  containers:
  - name: app
    image: my-dashboard
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/kubernetes.io/serviceaccount
      readOnly: true
```

**volumeMounts** = inside `containers[*]` (who mounts it). **volumes** = inside `spec` (what exists to mount). They connect by `name`.

### Assign SA to a deployment

```bash
kubectl set sa deploy <deploy-name> <sa-name>
# Argument order: <resource-type> <resource-name> <value>
```

## RBAC

```
Identity (SA or User) → RoleBinding → Role → permissions
```

```bash
kubectl create sa pod-reader-sa
kubectl create role pod-reader --verb=get,list,watch --resource=pods
kubectl create rolebinding pod-reader-binding --role=pod-reader --serviceaccount=default:pod-reader-sa
```

Check permissions:
```bash
kubectl auth can-i list pods --as=system:serviceaccount:default:my-sa
```

## Taints & Tolerations

**Taint** = "keep out" sign on a **node**. Repels pods.
**Toleration** = pod saying "I can handle that taint."

```bash
# Taint a node
kubectl taint nodes node1 gpu=true:NoSchedule

# Remove a taint (note the - suffix)
kubectl taint nodes node1 gpu=true:NoSchedule-

# See taints on nodes
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints
```

### Effects

| Effect | Meaning |
|---|---|
| `NoSchedule` | Don't schedule pods that don't tolerate |
| `PreferNoSchedule` | Try to avoid, soft rule |
| `NoExecute` | Evict existing pods that don't tolerate |

### Operators

| Operator | Meaning | Need `value`? |
|---|---|---|
| `Exists` | Match the key, any value | No — `value` must be empty |
| `Equal` | Match key and value exactly | Yes |

**Exam shortcut**: question says no value → `Exists`. Says a value → `Equal`.

### Example

```yaml
spec:
  tolerations:
  - key: "mortein"
    operator: "Exists"
    effect: "NoSchedule"
  containers:
  - name: bee
    image: nginx
```

**Important**: tolerations don't *attract* pods to a node — they only prevent rejection. To force a pod onto a specific node, use `nodeSelector` or `nodeAffinity`.

**Gotcha**: a pod must tolerate **all** taints on a node to be scheduled there, not just one.

## Troubleshooting pods

```bash
kubectl describe pod <name> | grep -A 5 -i event   # Why isn't it running?
kubectl get pod <name> -o yaml                      # Full spec
kubectl logs <name>                                 # App logs
kubectl logs <name> --previous                      # Crashed container logs
```

### Pending means one thing only

**The pod was never assigned to a node.** Not crashing, not pulling — never placed. So there's
exactly one component to interrogate: the scheduler. Its verdict is always in `describe` Events,
in plain English:

```
Warning  FailedScheduling  default-scheduler
0/1 nodes are available: 1 Insufficient cpu.
```

Common constraints it names: `Insufficient cpu/memory`, `node(s) had untolerated taint`,
`didn't match node selector`, `had volume node affinity conflict`.

Then quantify — supply vs. already-spoken-for vs. demand:

```bash
kubectl get node <node> -o jsonpath='{.status.allocatable.cpu}'   # supply
kubectl describe nodes | grep -A 10 "Allocated resources"          # already requested
kubectl get pod <name> -o jsonpath='{.spec.containers[*].resources}'  # demand
```

**The scheduler packs by `requests` — never `limits`, never actual usage.** A node sitting at 3%
CPU will still reject a pod whose request doesn't fit the unreserved remainder.

Worked example end to end: [KubeRay on kind](kuberay-on-kind.md).

## Exam speed workflow

1. `--dry-run=client -o yaml > file.yaml` → generate skeleton
2. `kubectl explain <path>` → look up fields you need
3. Edit the YAML, add what you learned
4. `kubectl apply -f file.yaml`
5. `kubectl describe` → check events if something's wrong

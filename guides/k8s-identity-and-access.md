# Kubernetes Identity & Access

> How K8s knows *who* is talking to the API server, and what they're allowed to do.

## Two kinds of identity

| | ServiceAccount | User Account |
|---|---|---|
| **What** | Identity for **pods/processes** inside the cluster | Identity for **humans** outside the cluster |
| **Managed by** | Kubernetes (API object: `ServiceAccount`) | External system (certs, OIDC, cloud IAM) |
| **Created how** | `kubectl create sa my-sa` | Not a K8s object — configured in kubeconfig or identity provider |
| **Namespaced** | Yes — each SA belongs to a namespace | No — users are cluster-wide |
| **Credentials** | Auto-mounted JWT token inside the pod | Client certs, bearer tokens, or OIDC tokens in `~/.kube/config` |

**Key insight**: Kubernetes has no "User" API object. When you run `kubectl`, your identity comes from your kubeconfig (`~/.kube/config`), which points to certs or tokens issued by something *outside* K8s (e.g., `kubeadm`, AWS IAM, Google Cloud IAM).

ServiceAccounts, on the other hand, are first-class K8s objects that pods use to authenticate to the API server.

## ServiceAccounts in depth

### Every pod has one

Every pod runs under a ServiceAccount. If you don't specify one, it uses `default` in its namespace.

```yaml
spec:
  serviceAccountName: my-sa   # explicit
```

### The token mount

By default, K8s mounts a JWT token into every pod at:

```
/var/run/secrets/kubernetes.io/serviceaccount/token
```

The pod uses this token to talk to the API server. That's how a dashboard app can list pods, or how a CI runner can create deployments.

### Why disable automount?

If your pod doesn't need to talk to the K8s API (most don't), the mounted token is an unnecessary attack surface. An attacker who compromises the pod gets API access for free.

```bash
# Disable on the ServiceAccount itself (affects all pods using it)
kubectl patch sa my-sa -p '{"automountServiceAccountToken": false}'
```

Or per-pod in the spec:

```yaml
spec:
  automountServiceAccountToken: false
```

### Manual token injection (projected volume)

When automount is disabled but your pod *does* need a token, you mount it explicitly with a projected volume. This gives you control over the mount path and makes it read-only:

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

**Why bother?** Projected tokens are time-bound and audience-scoped (more secure than the old never-expiring secrets). And `readOnly: true` prevents the process from tampering with its own credentials.

### Assigning a SA to an existing deployment

```bash
kubectl set sa deploy <deploy-name> <sa-name>
# Argument order: set sa <resource-type> <resource-name> <value>
# Same pattern as: kubectl set image deploy X container=image
```

## RBAC — connecting identity to permissions

Identity alone does nothing. RBAC controls what that identity can do.

```
Identity (SA or User) → RoleBinding → Role → permissions (verbs on resources)
```

### Role vs ClusterRole

- **Role**: permissions within a single namespace
- **ClusterRole**: permissions cluster-wide (or reusable across namespaces)

### Quick setup

```bash
# 1. Create the ServiceAccount
kubectl create sa pod-reader-sa

# 2. Create a Role (what can be done)
kubectl create role pod-reader --verb=get,list,watch --resource=pods

# 3. Bind them (who can do it)
kubectl create rolebinding pod-reader-binding \
  --role=pod-reader \
  --serviceaccount=default:pod-reader-sa
#                   ↑ namespace:sa-name
```

### Mental model

Think of it as a lock and key:
- **Role** = the lock (defines what doors exist and what actions are allowed)
- **ServiceAccount/User** = the person
- **RoleBinding** = giving that person the key to that lock

Without the binding, having a SA or having a Role does nothing — they must be connected.

## How to explore this during the exam

```bash
# What SA does a pod use?
kubectl get pod <name> -o jsonpath='{.spec.serviceAccountName}'

# What's mounted inside?
kubectl exec <pod> -- cat /var/run/secrets/kubernetes.io/serviceaccount/token

# What can a SA do?
kubectl auth can-i list pods --as=system:serviceaccount:default:my-sa

# Explore YAML fields you forgot
kubectl explain pod.spec.serviceAccountName
kubectl explain pod.spec.volumes.projected
```

`kubectl explain` drills into any field. You don't memorize the YAML — you look it up.

## Common CKAD patterns

| Scenario | What to do |
|---|---|
| Pod needs API access | Create SA → Role → RoleBinding → set `serviceAccountName` |
| Pod should NOT have API access | `automountServiceAccountToken: false` |
| Automount disabled but need token | Projected volume mount (see above) |
| Switch a deployment's SA | `kubectl set sa deploy <name> <sa>` |
| Check permissions | `kubectl auth can-i <verb> <resource> --as=system:serviceaccount:<ns>:<sa>` |

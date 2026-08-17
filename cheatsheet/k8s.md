# Kubernetes — CKAD

> Certified Kubernetes Application Developer exam domains.
> ponytail: imperative commands first — declarative YAML only when required.

## Exam Setup

```bash
alias k=kubectl
export do="--dry-run=client -o yaml"
export now="--force --grace-period 0"
# Generate YAML without creating:
k run nginx --image=nginx $do > pod.yaml
```

## Pods

```bash
k run nginx --image=nginx                          # Create pod
k run nginx --image=nginx --port=80                # With container port
k run tmp --image=busybox --rm -it -- sh           # Ephemeral debug pod
k run nginx --image=nginx $do > pod.yaml           # Generate YAML
k get pods -o wide                                 # Show node + IP
k get pod nginx -o yaml                            # Full spec
k describe pod nginx                               # Events + status
k delete pod nginx $now                            # Fast delete
k logs nginx                                       # Logs
k logs nginx -c sidecar                            # Specific container
k logs nginx --previous                            # Previous crash
k exec -it nginx -- sh                             # Shell into pod
k exec nginx -- env                                # Run command
```

## Deployments

```bash
k create deploy nginx --image=nginx --replicas=3
k scale deploy nginx --replicas=5
k set image deploy/nginx nginx=nginx:1.25
k rollout status deploy/nginx
k rollout history deploy/nginx
k rollout undo deploy/nginx                        # Rollback last
k rollout undo deploy/nginx --to-revision=2        # Rollback specific
k rollout restart deploy/nginx                     # Restart all pods
```

## Services

```bash
k expose pod nginx --port=80 --target-port=80 --name=nginx-svc
k expose deploy nginx --port=80 --type=ClusterIP
k expose deploy nginx --port=80 --type=NodePort
k get svc
k get ep                                           # Endpoints
```

```yaml
# ClusterIP (default)
apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
```

## ConfigMaps

```bash
k create cm app-config --from-literal=ENV=prod --from-literal=LOG=debug
k create cm app-config --from-file=config.txt
k get cm app-config -o yaml
```

```yaml
# Use as env vars
envFrom:
  - configMapRef:
      name: app-config

# Use specific key
env:
  - name: ENV
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: ENV

# Use as volume
volumes:
  - name: config-vol
    configMap:
      name: app-config
```

## Secrets

```bash
k create secret generic db-creds --from-literal=user=admin --from-literal=pass=s3cret
k get secret db-creds -o jsonpath='{.data.pass}' | base64 -d
```

```yaml
# Use as env
envFrom:
  - secretRef:
      name: db-creds

# Use as volume (files)
volumes:
  - name: secret-vol
    secret:
      secretName: db-creds
```

## Multi-Container Pods

```yaml
# Sidecar
spec:
  containers:
    - name: app
      image: nginx
    - name: sidecar
      image: busybox
      command: ["sh", "-c", "while true; do echo sync; sleep 30; done"]

# Init container (runs before main)
spec:
  initContainers:
    - name: init-db
      image: busybox
      command: ["sh", "-c", "until nslookup db-svc; do sleep 2; done"]
  containers:
    - name: app
      image: myapp
```

## Probes

```yaml
# Liveness — restart if fails
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10

# Readiness — remove from service if fails
readinessProbe:
  tcpSocket:
    port: 3306
  initialDelaySeconds: 5

# Startup — protect slow-starting apps
startupProbe:
  httpGet:
    path: /ready
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

## Resources

```yaml
resources:
  requests:
    memory: "64Mi"
    cpu: "250m"
  limits:
    memory: "128Mi"
    cpu: "500m"
```

## Jobs & CronJobs

```bash
k create job pi --image=perl -- perl -Mbignum=bpi -wle 'print bpi(2000)'
k create cronjob backup --image=busybox --schedule="0 2 * * *" -- /bin/sh -c "echo backup"
```

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  completions: 5          # Run 5 times total
  parallelism: 2          # 2 at a time
  backoffLimit: 4         # Retries before fail
  activeDeadlineSeconds: 60
  template:
    spec:
      containers:
        - name: pi
          image: perl
          command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
```

## Volumes & PVCs

```yaml
# Pod with emptyDir (shared between containers)
volumes:
  - name: shared
    emptyDir: {}

# Pod with hostPath
volumes:
  - name: data
    hostPath:
      path: /data
      type: DirectoryOrCreate

# PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi

# Mount PVC in pod
volumes:
  - name: data
    persistentVolumeClaim:
      claimName: my-pvc
containers:
  - volumeMounts:
      - mountPath: /data
        name: data
```

## NetworkPolicy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 80
```

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: my-svc
                port:
                  number: 80
```

## ServiceAccounts & RBAC

```bash
k create sa my-sa
k create role pod-reader --verb=get,list,watch --resource=pods
k create rolebinding pod-reader-binding --role=pod-reader --serviceaccount=default:my-sa
```

```yaml
# Pod with custom SA
spec:
  serviceAccountName: my-sa
  automountServiceAccountToken: false  # ponytail: disable if not needed
```

## Labels & Selectors

```bash
k label pod nginx env=prod
k label pod nginx env-                             # Remove label
k get pods -l env=prod
k get pods -l 'env in (prod,staging)'
k get pods -l env!=dev
k annotate pod nginx description="web server"
```

## Namespaces

```bash
k create ns dev
k get pods -n dev
k get pods -A                                      # All namespaces
k config set-context --current --namespace=dev     # Switch default ns
```

## Security Context

```yaml
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
```

## Helm (CKAD scope)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm search repo nginx
helm install my-release bitnami/nginx
helm list
helm upgrade my-release bitnami/nginx --set replicaCount=3
helm rollback my-release 1
helm uninstall my-release
```

## Exam Speed Tips

```bash
# YAML from existing resource
k get deploy nginx -o yaml > deploy.yaml

# Edit live
k edit deploy nginx

# Replace from file (delete + create)
k replace -f pod.yaml $now

# Explain any field
k explain pod.spec.containers.livenessProbe

# JSONPath
k get pods -o jsonpath='{.items[*].metadata.name}'
k get nodes -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}'

# Sort
k get pods --sort-by=.metadata.creationTimestamp

# All resources in namespace
k api-resources --namespaced=true
```

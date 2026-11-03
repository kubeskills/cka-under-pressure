# Baseline — reference solution

> **Spoiler.** Attempt `tasks/baseline.md` first (use `hints/baseline/` if you are stuck).
> This is **one valid solution**, not the only correct one. Anything that meets the
> acceptance criteria is correct.

Assumes `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"`.

## Solution

```bash solution
# Orient: right context, then what exists.
kubectl config current-context
kubectl -n drill-baseline get deployment,pods -o wide

# Read the one fact the brief does not give: the port the container declares.
kubectl -n drill-baseline get deployment web -o jsonpath='{.spec.template.spec.containers[0].ports}{"\n"}'

# Smallest change 1: size the Deployment.
kubectl -n drill-baseline scale deployment web --replicas=3
kubectl -n drill-baseline rollout status deployment web --timeout=120s

# Smallest change 2: a ClusterIP Service on port 80 that targets the container's port.
kubectl -n drill-baseline expose deployment web --port=80 --target-port=8080

# Verify behavior, not the command: who did the Service select?
kubectl -n drill-baseline get endpointslices -l kubernetes.io/service-name=web

# Verify like a client, from inside the namespace.
kubectl -n drill-baseline run client --rm -i --restart=Never --image=busybox:1.37.0 -- wget -qO- -T 2 http://web:80/
```

Then run the lab check:

```bash
scripts/verify.sh baseline
```

## Why this satisfies each criterion

| Criterion | Why |
|---|---|
| AC1 | `scale` sets 3 replicas; `rollout status` waits until they are Ready. |
| AC2 | `expose` creates a Service named after the Deployment, type ClusterIP by default, on port 80. |
| AC3 | `--target-port=8080` is the port the container declares, so connections reach the app. |
| AC4 | `expose` copies the Deployment's own selector (`app.kubernetes.io/name=web`, `tier=frontend`), which `report` does not satisfy; kube-proxy spreads connections over the three ready endpoints. |
| AC5 | Neither `report`, the NetworkPolicy, nor the `web` image was touched. |

## Common wrong turns

- **`kubectl expose deployment web --port=80` with no target port.** The command succeeds
  and prints `service/web exposed`, but the Service then targets port 80 while the app
  listens on 8080 — connections are refused. (Confirm this on your kubectl version; the
  presenter runbook uses it as the controlled mistake.) A successful command is not proof.
- **Selecting on `tier=frontend` alone.** Both `web` and `report` carry it, so `report`
  answers some requests (AC4 fails).
- **Exposing with NodePort/LoadBalancer or `port-forward`.** The brief asks for a
  cluster-internal name; `port-forward` tests your laptop's path, not a Pod's.
- **Creating a second Deployment** instead of scaling `web`. AC1 and the "may change" list
  point at the existing one.
- **Verifying only that Pods are Running.** Running is not the same as reachable.

## Limitations

- AC4 samples 12 requests. If the three `web` Pods are all Ready, the chance that every
  request lands on one Pod by chance is about 6 in a million under uniform balancing.
- The check does not judge style; it accepts any manifest-equivalent result.

# Variation A — reference solution

> **Spoiler.** Attempt `tasks/variation-a.md` first (use `hints/variation-a/` if stuck).
> This is **one valid solution**, not the only correct one.

Assumes `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"`.

## Solution

```bash solution
# Orient: right context, then follow the request path from the symptom.
kubectl config current-context
kubectl -n drill-variation-a get service web -o wide
kubectl -n drill-variation-a get endpointslices -l kubernetes.io/service-name=web

# Compare what the Service looks for with what the Pods carry.
kubectl -n drill-variation-a get pods --show-labels

# Smallest change that leaves the Deployment (and its running Pods) untouched:
# point the Service at the label that identifies only the web Pods.
kubectl -n drill-variation-a set selector service web app.kubernetes.io/name=web

# Verify behavior: the Service should now list three backend addresses.
kubectl -n drill-variation-a get endpointslices -l kubernetes.io/service-name=web

# Verify like a client, from inside the namespace.
kubectl -n drill-variation-a run client --rm -i --restart=Never --image=busybox:1.37.0 -- wget -qO- -T 2 http://web:80/
```

Then run the lab check:

```bash
scripts/verify.sh variation-a
```

## The fault, and why this fixes it

The Service selects Pods with `app=web`, but the `web` Pods are labelled
`app.kubernetes.io/name=web` and `tier=frontend`. A Service routes only to Pods whose
labels match its selector, so it had no endpoints and requests were not answered.

| Criterion | Why |
|---|---|
| AC1 | Unchanged — the Deployment was healthy and still is. |
| AC2 | The Service keeps its name, type and port; only its selector changed. |
| AC3 | With a matching selector the Service has endpoints; port 80 maps to the container's port 8080. |
| AC4 | `app.kubernetes.io/name=web` matches only `web` Pods; `report` has a different value. |
| AC5 | The Deployment spec was not touched (generation stays 1), so Pods were not rolled. |
| AC6 | `report`, the NetworkPolicy and the `web` image are untouched. |

## Other valid approaches

- Replace the selector with `app.kubernetes.io/name=web,tier=frontend` (both labels).
- Edit the Service with `kubectl edit` or `kubectl patch` (remember that a merge patch
  keeps old keys unless you null them).
- Delete the Service and recreate it with `kubectl expose deployment web --port=80
  --target-port=8080`, which copies the Deployment's selector.

## Common wrong turns

- **Adding `app: web` to the Deployment's Pod template.** It "works", but it rolls every
  Pod, which the brief forbids (AC5 fails).
- **Re-creating the Service the quick way** with `kubectl create service clusterip web
  --tcp=80:80`: that command's default selector is `app=<name>` — the same mismatch.
- **Selecting on `tier=frontend` alone.** `report` shares it; AC4 fails.
- **Restarting Pods** hoping it helps. The Pods were never the problem.

## Limitations

- AC5 uses the Deployment's `metadata.generation`; it flags any spec change, including
  harmless ones. That is intentional for this drill.

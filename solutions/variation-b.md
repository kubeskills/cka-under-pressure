# Variation B — reference solution

> **Spoiler.** Attempt `tasks/variation-b.md` first (use `hints/variation-b/` if stuck).
> This is **one valid solution**, not the only correct one.

Assumes `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"`.

## Solution

```bash solution
# Orient: right context, then Pod state. Running is not Ready.
kubectl config current-context
kubectl -n drill-variation-b get pods
kubectl -n drill-variation-b describe pod -l app.kubernetes.io/name=web

# Read the readiness check the kubelet is running.
kubectl -n drill-variation-b get deployment web -o jsonpath='{.spec.template.spec.containers[0].readinessProbe}{"\n"}'

# Confirm what the app actually serves (it logs the requests it receives).
kubectl -n drill-variation-b logs -l app.kubernetes.io/name=web --tail=5

# Smallest change: make the check ask for a path the app serves. Keep the check.
kubectl -n drill-variation-b patch deployment web --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/healthz"}]'
kubectl -n drill-variation-b rollout status deployment web --timeout=180s

# Verify behavior: every backend endpoint must be marked ready. (Addresses are listed
# even while not ready, so the address list alone proves nothing.)
kubectl -n drill-variation-b get endpointslices -l kubernetes.io/service-name=web -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{" ready="}{.conditions.ready}{"\n"}{end}'

# Verify like a client, from inside the namespace.
kubectl -n drill-variation-b run client --rm -i --restart=Never --image=busybox:1.37.0 -- wget -qO- -T 2 http://web:80/
```

Then run the lab check:

```bash
scripts/verify.sh variation-b
```

## The fault, and why this fixes it

The readiness check requests `/ready`, a path the application does not serve (it
answers 404). The Pods run but are never marked Ready, so none of the Service's
endpoints is ready and clients get no answer. Note that the EndpointSlice still *lists*
the three Pod addresses; each is marked `ready: false`, and a Service only routes to
ready endpoints. The Service and the Pods were fine; the check was asking for the wrong thing.

| Criterion | Why |
|---|---|
| AC1 | The corrected check passes, so the rolling update ends with 3/3 Ready. |
| AC2 | Service untouched. |
| AC3 | The readiness check is still defined — only its path changed. |
| AC4 | Once Pods are Ready their endpoints are marked ready, so requests are answered. |
| AC5 | Only `web` Pods answer, spread across the three. |
| AC6 | `report`, the NetworkPolicy and the `web` image are untouched. |

## Other valid approaches

- `kubectl edit deployment web` and change the path.
- Change the check to a TCP check on the container port (still a readiness check).

## Common wrong turns

- **Deleting the readiness check.** Pods turn Ready and the symptom vanishes, but the
  team's rule — unhealthy Pods never receive traffic — is broken (AC3 fails).
- **Setting `publishNotReadyAddresses` on the Service.** Same problem, different place
  (AC3 also checks for this).
- **Deleting Pods.** The Deployment recreates them with the same bad check.
- **Looking only at the Service.** It was correct; the Pod state is the lead.
- **Verifying before the rollout finishes.** The patch triggers a rolling update; wait
  for `rollout status` (or rely on `verify.sh`'s grace window).

## Limitations

- AC3 only checks that *a* readiness check exists and the Service does not bypass it. It
  cannot judge whether the check is meaningful (a check that always passes would satisfy
  it). Judging check quality is the learner's and reviewer's job.

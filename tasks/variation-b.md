# Task: Variation B — `web` is up, but nobody gets an answer

**Scenario id:** `variation-b` · **Namespace:** `drill-variation-b` · **Seed it with:** `scripts/reset.sh variation-b`

> This is original workshop practice material. It is not an exam question and does not
> reproduce the real exam environment.

## Scenario

After a change last night, requests to `http://web:80/` from Pods in this namespace
fail. The `web` Pods exist and are not crashing, and a Service named `web` is in place.
A second workload (`report`) shares the namespace and is working; leave it alone.

This team's rule: **an unhealthy `web` Pod must never receive traffic.** Whatever you
do, that guarantee stays in place.

## Where you work

| | |
|---|---|
| Cluster | The dedicated lab cluster (kind). |
| kubeconfig | `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"` |
| Context | `kind-cka-tip-talk` (confirm it before you change anything) |
| Namespace | `drill-variation-b` |

## Required outcome

1. `http://web:80/` works from inside the namespace.
2. All three `web` Pods are Ready, and the load is spread across them.
3. Only healthy Pods receive traffic, as before.

## You may change

- Deployment `web`
- Anything you create in `drill-variation-b`

## Must remain intact

- Service `web` (type ClusterIP, port 80)
- Deployment `report` (1 replica, Ready, same image)
- NetworkPolicy `allow-same-namespace`
- The container image used by `web`

## Acceptance criteria

These are exactly what `scripts/verify.sh variation-b` checks.

- **AC1** — Deployment `web` has 3 replicas, all Ready
- **AC2** — Service `web` is type ClusterIP and exposes port 80
- **AC3** — Health checking on the `web` container is still in place
- **AC4** — Requests to the Service on port 80 from inside the namespace succeed
- **AC5** — Only `web` Pods answer, and more than one of them does
- **AC6** — Protected resources are intact (`report`, the `web` image, NetworkPolicy)

A successful `kubectl` command is not proof that a criterion is met. Test the behavior.

## Practice mode and timebox

These durations are **workshop suggestions, not exam rules**, and they are unmeasured
starting points.

| Mode | Suggestion |
|---|---|
| Learning | No timer. Use the docs and hints. |
| Independent | About 10 minutes, no walkthrough. |
| Timed | About 6 minutes, only after an independent run succeeded without hints. |

## Check your work

```bash
scripts/verify.sh variation-b
scripts/verify.sh --diagnose variation-b   # optional: read-only observations, no advice
```

Note: a verify run that starts with Pods not Ready waits up to 10 seconds for them
(the `--grace` window), so expect roughly 15–20 seconds for the first run on this scenario.

Hints: `hints/variation-b/`. Reference solution: `solutions/variation-b.md` (open it last).
Reset to try again: `scripts/reset.sh variation-b`.

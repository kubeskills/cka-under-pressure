# Task: Variation A — the orders team can't reach `web`

**Scenario id:** `variation-a` · **Namespace:** `drill-variation-a` · **Seed it with:** `scripts/reset.sh variation-a`

> This is original workshop practice material. It is not an exam question and does not
> reproduce the real exam environment.

## Scenario

The orders team reports that requests to `http://web:80/` from their Pods in this
namespace fail. The platform team says the frontend itself looks healthy. A second
workload (`report`) shares the namespace and is working; leave it alone.

The frontend is serving live traffic for other consumers, so its running Pods must
not be restarted or replaced while you fix this.

## Where you work

| | |
|---|---|
| Cluster | The dedicated lab cluster (kind). |
| kubeconfig | `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"` |
| Context | `kind-cka-tip-talk` (confirm it before you change anything) |
| Namespace | `drill-variation-a` |

## Required outcome

1. `http://web:80/` works from inside the namespace.
2. Only `web` Pods answer, and the load is spread across all three.
3. Nothing else changes: the running `web` Pods keep running.

## You may change

- Anything in `drill-variation-a` **except** the items below

## Must remain intact

- The running `web` Pods (no restarts, no replacement; the Deployment's spec stays as it is)
- Deployment `report` (1 replica, Ready, same image)
- NetworkPolicy `allow-same-namespace`
- The Service keeps its name `web`, type ClusterIP, and port 80

## Acceptance criteria

These are exactly what `scripts/verify.sh variation-a` checks.

- **AC1** — Deployment `web` has 3 replicas, all Ready
- **AC2** — Service `web` is type ClusterIP and exposes port 80
- **AC3** — Requests to the Service on port 80 from inside the namespace succeed
- **AC4** — Only `web` Pods answer, and more than one of them does
- **AC5** — The live `web` Pods were not restarted or replaced
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
scripts/verify.sh variation-a
scripts/verify.sh --diagnose variation-a   # optional: read-only observations, no advice
```

Hints: `hints/variation-a/`. Reference solution: `solutions/variation-a.md` (open it last).
Reset to try again: `scripts/reset.sh variation-a`.

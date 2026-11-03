# Task: Baseline — make the shop frontend reachable

**Scenario id:** `baseline` · **Namespace:** `drill-baseline` · **Seed it with:** `scripts/reset.sh baseline`

> This is original workshop practice material. It is not an exam question and does not
> reproduce the real exam environment.

## Scenario

The shop team's web frontend (`web`) is deployed, but it is under-provisioned for
tomorrow's traffic and nothing else in the cluster can reach it by name. A second
workload (`report`) shares the namespace and must not be disturbed.

Everything you need to know about the application is in the cluster, not in this brief.

## Where you work

| | |
|---|---|
| Cluster | The dedicated lab cluster (kind). |
| kubeconfig | `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"` |
| Context | `kind-cka-tip-talk` (confirm it before you change anything) |
| Namespace | `drill-baseline` |

## Required outcome

1. The `web` application runs with **3 replicas**, all Ready.
2. Other Pods in the namespace can reach the web application at **`http://web:80/`**
   through a stable, cluster-internal name. It must **not** be exposed outside the cluster.
3. Only `web` Pods answer on that name, and the load is spread across the `web` Pods.

## You may change

- Deployment `web`
- Anything you create in `drill-baseline`

## Must remain intact

- Deployment `report` (1 replica, Ready, same image)
- NetworkPolicy `allow-same-namespace`
- The container image used by `web`

## Acceptance criteria

These are exactly what `scripts/verify.sh baseline` checks.

- **AC1** — Deployment `web` has 3 replicas, all Ready
- **AC2** — A Service named `web` exists, type ClusterIP, port 80
- **AC3** — Requests to the Service on port 80 from inside the namespace succeed
- **AC4** — Only `web` Pods answer, and more than one of them does
- **AC5** — Protected resources are intact (`report`, the `web` image, NetworkPolicy)

A successful `kubectl` command is not proof that a criterion is met. Test the behavior.

## Practice mode and timebox

These durations are **workshop suggestions, not exam rules**, and they are unmeasured
starting points. Adjust them after you have timed yourself.

| Mode | Suggestion |
|---|---|
| Learning | No timer. Use the docs, use hints, understand each step. |
| Independent | About 15 minutes, no walkthrough. Hints allowed; log which ones. |
| Timed | About 8 minutes, only after an independent run succeeded without hints. |

## Check your work

```bash
scripts/verify.sh baseline
scripts/verify.sh --diagnose baseline   # optional: read-only observations, no advice
```

Stuck? Hints are in `hints/baseline/` (level 1 first). Reference solution: `solutions/baseline.md`
— open it last. Reset to try again: `scripts/reset.sh baseline`.

# Adapting this kit to Killercoda or another disposable environment

> **Status: a design note, not an integration.** Nothing here has been built or tested on
> Killercoda or any other platform. Check that platform's current documentation before
> relying on any of the assumptions below.

## What is already portable

| Asset | Why it ports |
|---|---|
| `lab/base/`, `lab/scenarios/*/` | Plain Kubernetes manifests composed with kustomize. `kubectl apply -k lab/scenarios/<id>` works on any cluster whose `kubectl` is recent enough to bundle kustomize. They use only stable APIs (`v1`, `apps/v1`, `networking.k8s.io/v1`). |
| `tasks/*.md`, `hints/`, `solutions/`, `worksheets/` | Pure Markdown. Namespaces and names are fixed (`drill-<id>`), so they do not depend on kind. |
| `scripts/lib/verify.py` | Standard library only. It needs `kubectl`, a kubeconfig, and the namespace; it creates one short-lived labelled Pod and removes it. |

## What is kind-specific

| Asset | Replace with |
|---|---|
| `scripts/cluster-up.sh`, `cluster-down.sh`, `lab/kind-cluster.yaml` | Nothing; the platform provides the cluster. |
| `scripts/lib/common.sh` `lab_guard` | A guard suited to the platform (for example: expected context name, no remote-API check). The current guard deliberately refuses anything that is not the local kind cluster. |
| `scripts/reset.sh` | Likely reduces to `kubectl delete ns` + `kubectl apply -k`, run by the platform's setup step. |

## Suggested approach (unverified)

1. Copy `lab/`, `tasks/`, `hints/`, `solutions/` into the course repository.
2. Use the platform's per-step setup hook to run `kubectl apply -k lab/scenarios/<id>`.
3. Use the platform's per-step verify hook to run `python3 scripts/lib/verify.py <id>` with
   `LAB_KUBECONFIG`, `LAB_CONTEXT` and `LAB_NAMESPACE` set for that environment. (The verifier
   refuses to run without them.)
4. Keep hints and solutions out of the step text; reveal them as separate steps or links.

## Things to check on the target platform

- Is the app image (`busybox`, pinned in `lab/base/app-template/deployment.yaml`) pullable?
- Does the cluster enforce NetworkPolicy, and does the probe Pod's same-namespace traffic work?
- Is `python3` ≥ 3.8 available where the verify hook runs?
- Is the platform's kubectl new enough to bundle kustomize?
- Pod Security: the scenario namespaces set `enforce: baseline`; confirm the platform allows that label.

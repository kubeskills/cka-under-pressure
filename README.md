# CKA Under Pressure: A Better Way to Practice

Companion kit for Chad Crowell's KubeCon NA 2026 tip talk.

> **Don't practice until the exercise feels familiar. Practice until you can solve it without the walkthrough.**

Make practice about *solving* problems, not following tutorials. This kit gives you a
repeatable **Read → Orient → Solve → Verify → Review** workflow, three small drills on a
disposable local cluster, hints that unlock in stages, and an automated check that tests
behavior instead of trusting that a command "worked".

**The timer is a diagnostic tool, not the goal of every session.** Learn the skill with no
pressure first, attempt it alone, verify it, review your mistakes, repeat with a variation,
and only then add time pressure. Fast typing is not competence.

## Lab checks are not the exam

- This is **original** practice material. It is not an exam question set and does not
  reproduce the real exam environment.
- `scripts/verify.sh` is a **lab check written for this workshop**. It is not official CKA
  scoring, and passing these drills does not guarantee passing the exam.
- For current exam requirements, rules, and what is permitted, use the official Linux
  Foundation page for the exam:
  <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>
  (and the Kubernetes docs at <https://kubernetes.io/docs/home/>). The only exam facts in this
  kit are in [`FAQ/cka-exam-faq.md`](FAQ/cka-exam-faq.md), each with its official source and
  the date it was checked; they can go stale, so confirm on the official pages.

## Start here

1. Skim the one-page workflow: [`takeaway/one-page.md`](takeaway/one-page.md) (print version: [`takeaway/one-page.html`](takeaway/one-page.html)).
2. Check [prerequisites](#prerequisites) and run the [quickstart](#quickstart).
3. Open [`tasks/baseline.md`](tasks/baseline.md) and work it **without** the solution.
4. Verify with `scripts/verify.sh baseline`. Use [hints](hints/) only when stuck, one level at a time.
5. Fill in [`worksheets/practice-worksheet.md`](worksheets/practice-worksheet.md), then classify
   what went wrong with [`worksheets/retrospective.md`](worksheets/retrospective.md).
6. A few days later, try [`tasks/variation-a.md`](tasks/variation-a.md) and
   [`tasks/variation-b.md`](tasks/variation-b.md), and then add a timer.

**Solutions are separate** and spoil the tasks: [`solutions/`](solutions/). Open them last.
Please also don't browse [`lab/scenarios/`](lab/scenarios/) before attempting a variation; it
contains the seeded faults.

## Prerequisites

- [ ] **Docker** (or a container runtime kind supports). This kit was tested with Docker Desktop.
- [ ] **kind** — <https://kind.sigs.k8s.io/docs/user/quick-start/#installation>
- [ ] **kubectl** — <https://kubernetes.io/docs/tasks/tools/> (recent enough to bundle kustomize)
- [ ] **python3 ≥ 3.8** (standard library only; used by the verifier)
- [ ] **bash** (the scripts run on macOS's bash 3.2 and on newer bash)
- [ ] **Network access** to pull two images the first time (see below). The kit does not
  claim offline support.
- [ ] About **1–2 GB** of free disk for the node image, and a few hundred MB of free memory
  for one extra single-node cluster. *(Estimates; unmeasured on your machine.)*

Nothing is installed for you. Scripts check prerequisites and stop with a message if one is missing:

```bash
scripts/preflight.sh
```

### What gets downloaded

| Image | Used for | When |
|---|---|---|
| `kindest/node:v1.34.0` (tag and digest pinned in [`lab/kind-cluster.yaml`](lab/kind-cluster.yaml)) | the kind node: the whole cluster runs inside this one Docker container | `scripts/cluster-up.sh`, pulled by Docker on your machine, unless already cached |
| `busybox:1.37.0` (tag pinned in [`lab/base/app-template/deployment.yaml`](lab/base/app-template/deployment.yaml)) | the `web` and `report` apps, and the verifier's probe Pod | first `scripts/reset.sh`, pulled by the kind node from Docker Hub |

## Quickstart

```bash
# 1. Check your tools (read-only).
scripts/preflight.sh

# 2. Create the dedicated kind cluster "cka-tip-talk" (asks before it creates anything).
#    One node, built from the image kindest/node:v1.34.0 (pinned in lab/kind-cluster.yaml).
scripts/cluster-up.sh

# 3. Point THIS terminal at the lab cluster (your ~/.kube/config is never modified).
export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"
kubectl config current-context        # expect: kind-cka-tip-talk

# 4. Start the baseline drill: creates namespace drill-baseline and deploys the lab app
#    (Deployments "web" and "report", container image busybox:1.37.0).
scripts/reset.sh baseline

# 5. Confirm it is running. The IMAGES column should show busybox:1.37.0.
kubectl -n drill-baseline get deployments,pods -o wide

# 6. Read the brief, then work the task without the solution.
cat tasks/baseline.md

# 7. Check your work. Add --diagnose for read-only observations (no advice).
scripts/verify.sh baseline
```

Start the others with `scripts/reset.sh variation-a` and `scripts/reset.sh variation-b`.

### What starting a drill does

You never run `kubectl apply` yourself; `scripts/reset.sh <scenario>` does it, so the starting state is
identical every time. It:

1. Checks that it is talking to the lab cluster (context `kind-cka-tip-talk`), or exits without changing anything.
2. Deletes the namespace `drill-<scenario>` first **if it already exists** (it asks before it does, and
   only for namespaces carrying this lab's ownership label).
3. Applies `lab/scenarios/<scenario>` with kustomize (`kubectl apply -k`). Output is hidden on purpose,
   so setup does not tell you what each scenario starts with.
4. Waits up to 3 minutes for the Pods to start.

Every `web` and `report` Pod runs `busybox httpd` on port 8080 from the same image, because both
Deployments are generated from one definition, `lab/base/app-template/deployment.yaml`. The image
list, with where each one comes from, is under [What gets downloaded](#what-gets-downloaded).

### Estimated time (estimates until measured)

| Phase | Estimate |
|---|---|
| First-time setup (network-dependent; image downloads) | 5–15 minutes |
| Repeat setup (images cached) | 1–3 minutes |
| One drill | 10–15 minutes independent; see each task for suggested timeboxes |

These are guesses. One measured data point from a single machine (cluster creation with the node
image already cached: about 30 seconds; first seed including the `busybox` download: about 7 seconds)
is in [`docs/validation-report.md`](docs/validation-report.md); your network and machine will differ.

### Tested configuration

Tested once, on macOS with bash 3.2: Docker Desktop 29.6.1, kind v0.30.0, kubectl client v1.34.2,
Kubernetes v1.34.0 (kind node, containerd 2.1.3), Python 3.14.5. Other combinations are **untested**
and are not claimed to be supported. Details and exactly what was and was not tested:
[`docs/validation-report.md`](docs/validation-report.md).

## The kit at a glance

| Task | Scenario | What it practices |
|---|---|---|
| [`baseline`](tasks/baseline.md) | Make `web` reachable and properly sized | Reading criteria, orienting, inspecting before changing, verifying real connectivity |
| [`variation-a`](tasks/variation-a.md) | One seeded fault in how clients reach `web` | Following a request path; a constraint on what you may change |
| [`variation-b`](tasks/variation-b.md) | A different single seeded fault | Same workflow, different relationship to inspect |

| Resource | Where |
|---|---|
| Hints (3 levels per task, separate files) | [`hints/`](hints/) |
| Reference solutions (one valid solution each) | [`solutions/`](solutions/) |
| Verification | [`scripts/verify.sh`](scripts/verify.sh), tested by [`tests/`](tests/) |
| Worksheet / retrospective | [`worksheets/`](worksheets/) |
| CKA exam FAQ (sourced, dated) | [`FAQ/cka-exam-faq.md`](FAQ/cka-exam-faq.md) |
| Presenter runbook | [`presenter/runbook.md`](presenter/runbook.md) |
| Validation report (what was and wasn't tested) | [`docs/validation-report.md`](docs/validation-report.md) |
| Adapting to a browser lab | [`docs/adapting-to-killercoda.md`](docs/adapting-to-killercoda.md) |
| Maintainer notes and open decisions | [`MAINTAINER-NOTES.md`](MAINTAINER-NOTES.md) |

## Verify, reset, clean up

| I want to… | Run |
|---|---|
| Check my work | `scripts/verify.sh <baseline\|variation-a\|variation-b>` |
| See observations without advice | `scripts/verify.sh --diagnose <scenario>` |
| Start a scenario over | `scripts/reset.sh <scenario>` (asks before deleting the namespace) |
| Reset everything | `scripts/reset.sh --all` |
| Remove lab namespaces, keep the cluster | `scripts/clean.sh` |
| Remove the cluster | `scripts/cluster-down.sh` |

Add `--yes` to skip confirmation prompts.

**Each scenario resets independently.** `reset.sh` deletes and recreates only the namespace
`drill-<scenario>`, and only if it carries the lab's ownership label
(`app.kubernetes.io/managed-by=cka-under-pressure`); it refuses otherwise. Cluster lifecycle
(`cluster-up.sh`, `cluster-down.sh`) is separate from namespace resets.

### What the verifier creates

`scripts/verify.sh` creates **one** short-lived Pod named `verify-probe-<hex>` in the scenario
namespace (labelled `app.kubernetes.io/component=verifier-probe`) so it can call the Service from
inside the cluster, then deletes it before exiting. Stale probes from interrupted runs are swept
at the start of the next run, selecting only Pods with the lab's labels. Running it repeatedly
leaves nothing behind.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All criteria PASS |
| 1 | At least one criterion FAILED — your solution does not yet meet the brief |
| 2 | Usage error |
| 3 | **Refused**: wrong or unexpected context/cluster; nothing was changed |
| 4 | **ERROR**: environment or verifier problem (cannot judge your solution) |
| 5 | Confirmation declined; nothing was changed |

## Safety model

- Scripts pass `--kubeconfig` **and** `--context` on every call and never read or write
  `~/.kube/config`. The lab's credentials live in `.kube/cka-tip-talk.kubeconfig` (git-ignored).
- Before any change, scripts require: the context `kind-cka-tip-talk`; a loopback API server
  address; and the node `cka-tip-talk-control-plane`. Otherwise they exit 3 without changing anything.
- Lab workloads are namespace-scoped. There are no privileged Pods, host mounts, cluster-admin
  bindings, load balancers or ingress controllers. Pods run non-root with dropped capabilities.
- **When you practice in your own terminal, `export KUBECONFIG=…` points `kubectl` at the lab
  cluster only for that shell.** Always confirm `kubectl config current-context` first; it is
  the first habit this kit is trying to build.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `Required command not found` / preflight `[FAIL]` | Install the named tool; re-run `scripts/preflight.sh`. |
| `The Docker daemon is not reachable` | Start Docker Desktop (or the docker service) and retry. |
| `kind create cluster` is slow or fails while downloading | Network/proxy issue pulling `kindest/node`. Retry on a stable network. |
| Exit 3: `Refusing to continue…` | Your `LAB_KUBECONFIG` points somewhere other than the lab cluster. Unset it, or run `scripts/cluster-up.sh`. Nothing was changed. |
| Exit 4: `Cannot reach the lab cluster API` | Docker stopped or the cluster is gone. `scripts/preflight.sh`, then `scripts/cluster-up.sh`. |
| `reset.sh` times out seeding | First run is downloading the app image; check network access and retry. |
| Pods `ImagePullBackOff` | The node cannot pull `busybox` (network, proxy, or registry rate limits). Retry later or on another network. |
| `verify.sh` prints `ERROR` | The check could not run; this is not a verdict on your solution. Run `scripts/preflight.sh`. |
| My `kubectl` hits the wrong cluster | Your shell has a different `KUBECONFIG`/context. `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"`. |
| Another kind cluster is also running | Fine; this kit only ever touches the one named `cka-tip-talk`. Mind your Docker memory limit. |
| `AlreadyExists` errors during `reset.sh`, or odd results from `verify.sh` | Two things are using the same lab at once (two terminals, or a test run plus a manual reset). The `drill-*` namespaces are shared state: run one reset, verify, or `tests/e2e.sh` at a time. |

## Layout

```
tasks/        outcome-based briefs with acceptance criteria
hints/        3 progressive hints per task (one file per level)
solutions/    reference solutions (spoilers)
worksheets/   practice worksheet, retrospective
takeaway/     one-page workflow sheet (Markdown + print-ready HTML)
presenter/    runbook and fallback sample output
lab/          kind config + kustomize manifests (contains seeded faults)
scripts/      preflight, cluster-up/down, reset, clean, verify
tests/        static checks, unit tests, end-to-end test
docs/         validation report, adaptation note
FAQ/          CKA exam FAQ (exam facts with official sources and check dates)
```

## Tests (for maintainers)

```bash
tests/run-static.sh      # no cluster needed
tests/e2e.sh --yes       # needs the lab cluster; mutates only drill-* namespaces in it
```

Licensed under the [MIT License](LICENSE). See [`MAINTAINER-NOTES.md`](MAINTAINER-NOTES.md) for maintainer notes.

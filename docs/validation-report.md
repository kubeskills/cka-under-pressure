# Validation report

Date of runs: 2026-11-03. One machine, one pass. "Tested" below means *observed in those
runs*; everything else is listed under [Untested assumptions](#untested-assumptions).
This kit's checks are lab checks, not official CKA scoring.

## Environment actually used

| Item | Version |
|---|---|
| OS / shell | macOS (Darwin 25.6.0, arm64), bash 3.2.57 |
| Docker | Docker Desktop 29.6.1 (client and server), 8 GB memory limit, 4 other kind nodes running |
| kind | v0.30.0 (go1.25.0) |
| kubectl client | v1.34.2 (kustomize v5.7.1 bundled) |
| Kubernetes server | v1.34.0 (`kindest/node:v1.34.0`, digest pinned in `lab/kind-cluster.yaml`), containerd 2.1.3, single control-plane node |
| App/probe image | `busybox:1.37.0` (pulled from Docker Hub by the node) |
| Python | 3.14.5 |
| shellcheck | v0.10.0, run from a locally cached image with `--network none` |

No other version combination was tested, so none is labelled "supported".

## Checks executed and results

### Static (no cluster) — `tests/run-static.sh`: 16 passed, 0 failed, 2 skipped

| Check | Result |
|---|---|
| `bash -n` on all 10 shell scripts | PASS |
| shellcheck v0.10.0 (`-x -P SCRIPTDIR`) on all scripts and tests | PASS (after fixing three findings; see below) |
| Python syntax | PASS |
| Verifier unit tests (`tests/test_verify.py`, fake kubectl) | PASS, 29 tests |
| Context-guard tests (`tests/test_guard.sh`, fake kubectl) | PASS, 24 checks |
| Rendered-manifest checks (`tests/check_manifests.py`, local `kubectl kustomize`) | PASS, 107 checks |
| Docs consistency (`tests/check_docs.py`) | PASS, 281 checks |
| **black** | **SKIPPED** (not installed) |
| **yamllint** | **SKIPPED** (not installed) |

Test quality: I mutated copies of the verifier eight ways (for example disabling the
stray-Pod check, the generation check, probe cleanup, and ERROR-over-FAIL precedence) and
every mutant was caught by the unit tests. Reintroducing the old ownership helper made the
guard suite fail.

### Live end-to-end — `tests/e2e.sh --yes`: 61 passed, 0 failed (second run)

Run against the real `cka-tip-talk` kind cluster. For each of `baseline`, `variation-a`,
`variation-b`:

1. Initial state FAILS verification (exit 1) with the expected criteria failing.
2. The documented reference solution (executed verbatim from `solutions/<id>.md`) passes.
3. Re-running verification twice more still passes, and no probe Pods are left behind.
4. Reset recreates the namespace (new UID) and restores the identical failing state.
5. Setup output does not contain solution vocabulary.

Also verified live:

- The presenter's controlled mistake (`expose` without a target port) succeeds as a
  command, fails AC3/AC4 with `connection refused`, and the runbook's recovery passes.
- A kubeconfig whose context is not the lab's is refused with exit 3 by `reset.sh`
  (single and `--all`), `clean.sh`, and `verify.sh`, and the `drill-baseline` namespace UID
  is unchanged afterwards. An unrelated `KUBECONFIG` in the environment is ignored.
- `reset.sh` refuses, and `clean.sh` skips, an unlabelled namespace named like a lab one.
- `verify.sh --diagnose` prints read-only observations without advice.
- `scripts/cluster-up.sh`, `scripts/preflight.sh`, `scripts/clean.sh` behave as documented.
- `scripts/cluster-down.sh` declines (exit 5) without confirmation and deletes nothing.
- Your default kubeconfig was untouched: SHA-256 of `~/.kube/config` and the current
  context (`kind-otel-lab`) were identical before and after cluster creation; the only
  differences were the new kind cluster and its one container.

### Print check

`takeaway/one-page.html` rendered with headless Chrome to **one US-Letter page**; text was
legible and nothing clipped. (Two pages before the CSS was tightened.)

## Problems found by validation, and fixed

| Found by | Problem | Fix |
|---|---|---|
| shellcheck | A comment was parsed as a directive; `source` paths not followed; library constants flagged unused | Reworded; `-P SCRIPTDIR`; file-level SC2034 note in `common.sh` |
| Print render | Takeaway footer spilled onto page 2 | Tightened spacing |
| **Live e2e (run 1: 37 passed, 24 failed)** | `ns_is_lab_owned` used `kubectl get namespace NAME -l …`, which kubectl rejects (`name cannot be provided when a selector is specified`). Every reset of an *existing* namespace was refused. It failed safe (refused rather than deleted), but reset was broken. | List owned namespaces and match by exact name; added regression tests to the guard suite |
| Live inspection | In `variation-b`, EndpointSlices list all three Pod addresses even though no Pod is Ready (`ready: false`). My solution's "three backend addresses" check proved nothing. | Solution and hint 2 now inspect per-endpoint `ready`; the explanation says so |
| Debugging | Sourcing `common.sh` from zsh miscomputed the repo root (zsh has no `BASH_SOURCE`) | `common.sh` now refuses to be sourced outside bash |
| Concurrent use | Another session ran `tests/e2e.sh` against the same cluster while I reset a namespace; `AlreadyExists` errors | Documented in README and maintainer notes; no locking added |

## Measured numbers (one machine, so treat as data points, not promises)

| Step | Measured |
|---|---|
| `cluster-up.sh`, node image already cached | about 30 s (kind reported "Ready after 17s") |
| First `reset.sh` including the `busybox` download | about 7 s |
| Later `reset.sh` of one scenario | about 4 s |
| `verify.sh baseline` on the initial state | about 3 s |
| `verify.sh variation-b` on the initial state (waits 10 s for Ready) | about 19 s |
| Full `tests/e2e.sh` | 660 s (the other session may have contended for the cluster) |

## How to reproduce

```bash
tests/run-static.sh                       # no cluster
scripts/preflight.sh
scripts/cluster-up.sh --yes               # creates cluster "cka-tip-talk"
tests/e2e.sh --yes --log /tmp/e2e.log     # mutates drill-* namespaces only
scripts/cluster-down.sh --yes             # optional teardown
```

## Untested assumptions

- **`scripts/cluster-down.sh` actually deleting the cluster.** Only its decline path ran.
- **Cluster creation when the node image is not cached**, and the real download size/time.
- **Offline operation.** Not claimed; not tested.
- **Other versions** of kubectl, kind, Kubernetes, Docker, Python (only 3.14.5 was run; ≥ 3.8
  is the intent), bash (only 3.2 was run), or OS (no Linux run). Other container runtimes
  (podman) were not tried.
- **NetworkPolicy enforcement.** The policy is accepted by the API server; whether this
  kind CNI enforces it was not tested, and the lab does not depend on it.
- **A4 printing** (the sheet forces US Letter), and printing from non-Chrome browsers.
- **Docker Hub rate limits or conference Wi‑Fi.** One pull succeeded on one network.
- **Suggested timeboxes** in `tasks/*.md` are unmeasured guesses.
- **Human usability.** No attendee has attempted the drills; hint quality is unpiloted.
- **The runbook's pacing** has not been rehearsed against a clock, and the talk length is unconfirmed.
- **Killercoda or any browser lab.** `docs/adapting-to-killercoda.md` is a design note only.

## Known limitations

- AC4 samples 12 requests; with three Ready Pods and uniform balancing the chance of a
  false FAIL from all requests landing on one Pod is about 6 in a million (a calculation,
  not a measurement).
- `variation-a` AC5 uses the Deployment's `metadata.generation`, so it flags any spec
  change, including harmless ones.
- `variation-b` AC3 checks that *a* readiness check exists and is not bypassed; it cannot
  judge whether the check is meaningful.
- The verifier needs a working image pull for its probe Pod (same image as the app).
- The lab namespaces are shared state; do not run two resets or e2e runs concurrently.
- The kit makes no claims about the CKA exam. Its two outbound exam links were copied from
  the author's resource list and were not re-fetched.

## Remaining manual review

- Run black and yamllint (not available here) and fix what they report.
- Rehearse the runbook on the presenting machine, including the `expose` mistake on its kubectl.
- Pilot the drills with one or two people and adjust hints and timeboxes.
- Print the takeaway and check the QR code resolves (the QR image file was added outside
  this validation and was not checked).
- Confirm the MIT license scope in `MAINTAINER-NOTES.md`.

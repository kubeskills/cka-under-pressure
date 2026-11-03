# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A workshop companion kit (not an application) for a KubeCon NA 2026 CKA-practice talk: three drills (`baseline`, `variation-a`, `variation-b`) run against a disposable kind cluster named `cka-tip-talk`. Most of the repo is learner-facing Markdown; the code is the lab tooling (bash + stdlib-only Python) and the tests that keep docs, manifests, and the verifier consistent. `README.md` is attendee-facing; `MAINTAINER-NOTES.md` holds open decisions (the MIT license scope, the repo URL and QR code on the `takeaway/` sheet).

## Commands

```bash
tests/run-static.sh        # all no-cluster checks: bash -n, shellcheck, black, yamllint, unit + doc + manifest checks
tests/e2e.sh --yes         # needs the live lab cluster; resets/deletes drill-* namespaces in it (requires --yes)
tests/test_guard.sh        # context-guard test using a fake kubectl on PATH

python3 -m unittest discover -s tests -p 'test_verify.py'                       # verifier unit tests
python3 -m unittest tests.test_verify.BaselineTests.test_solved_state_passes    # single test
python3 tests/check_docs.py        # docs, hints, solutions and tasks vs. verifier consistency
python3 tests/check_manifests.py   # rendered kustomize manifests

scripts/preflight.sh                      # read-only tool check
scripts/cluster-up.sh / cluster-down.sh   # create/remove the kind cluster
export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"   # point a shell at the lab
scripts/reset.sh [--yes] <scenario>|--all
scripts/verify.sh [--diagnose] [--grace N] <scenario>
scripts/clean.sh                          # remove lab namespaces, keep cluster
```

shellcheck, black, and yamllint are optional in `run-static.sh`: missing tools report SKIP (never PASS). `e2e.sh` has no single-scenario flag; it loops over all three.

## Architecture

**Safety guard is the core invariant.** Every script sources `scripts/lib/common.sh` and calls `lab_guard` before mutating anything. All kubectl calls go through `lab_kubectl`, which passes `--kubeconfig` and `--context` explicitly; `~/.kube/config` is never read or written. The guard requires context `kind-cka-tip-talk`, a loopback API server, and node `cka-tip-talk-control-plane`, else exit 3 with no changes. `reset.sh` additionally only deletes namespaces carrying label `app.kubernetes.io/managed-by=cka-under-pressure`. Preserve this when adding scripts; `tests/test_guard.sh` asserts no mutating kubectl verb is reached before the guard passes.

**Exit-code contract** (defined in `common.sh`, documented in `README.md`): 0 pass, 1 criterion FAIL, 2 usage, 3 refused, 4 environment/verifier ERROR, 5 confirmation declined. FAIL (user's solution wrong) and ERROR (verifier couldn't judge) must stay distinct.

**Scenario pipeline.** `lab/base/{app-template,web,web-service,report}` + `networkpolicy.yaml` are kustomize bases. Each `lab/scenarios/<id>/` overlay applies the namespace `drill-<id>`, the ownership label, and a JSON patch that seeds the fault (these overlays are spoilers). `reset.sh` applies the overlay with output discarded (so setup doesn't leak the fault) and waits for the seeded state; `variation-b` seeds Pods that never become Ready, hence the special case in `seed_ready`.

**Verifier** (`scripts/lib/verify.py`, invoked via `verify.sh`, which exports `LAB_KUBECONFIG`/`LAB_CONTEXT`/`LAB_NAMESPACE`): a `SCENARIOS` dict maps each scenario to a list of `Criterion(id, title, check)`. It tests behavior, not config, by launching one labelled `verify-probe-<hex>` Pod to call the Service from inside the cluster, then deleting it (stale probes swept on next run). The app image is read from `lab/base/app-template/deployment.yaml` via `manifest_image`, the single source for the pin.

**Docs are tested as code.** `tests/check_docs.py` imports `verify` and enforces: criterion titles in `verify.py` match `tasks/<id>.md` exactly; task briefs contain no solution vocabulary (`targetPort`, `selector`, `kubectl expose`, …); hints/solutions exist per scenario. `tests/e2e.sh` executes fenced blocks tagged ` ```bash solution ` in `solutions/<id>.md` and ` ```bash demo-mistake ` / ` demo-recover ` in `presenter/runbook.md` verbatim, so edits to those blocks must remain runnable.

## Keeping things in sync

- Changing acceptance-criteria text: update `tasks/<id>.md` **and** `scripts/lib/verify.py`.
- `takeaway/one-page.md` and `.html` are hand-synced.
- Adding a scenario: add the id to `LAB_SCENARIOS` (`common.sh`), `SCENARIOS` (`verify.py`), the loops in `tests/e2e.sh` (and the `SCENARIOS` list in `tests/check_docs.py`), plus `lab/scenarios/<id>/`, `tasks/<id>.md`, `hints/<id>/level-{1,2,3}.md`, `solutions/<id>.md`. Full steps in `MAINTAINER-NOTES.md`.

## Conventions specific to this repo

- Scripts must run on macOS bash 3.2: no associative arrays, `mapfile`, or `${var,,}`; use `${arr[@]+"${arr[@]}"}` for possibly-empty arrays under `set -u`. `common.sh` refuses to be sourced from zsh/sh.
- Python is standard library only, ≥ 3.8 (`from __future__ import annotations`), black-formatted.
- Spoiler hygiene: don't put solution hints in task briefs, setup output, or comments outside `lab/scenarios/`; don't make claims about current CKA exam requirements (link to the Linux Foundation page instead).
- `.kube/` and `*.kubeconfig` are git-ignored (lab credentials); never commit them.

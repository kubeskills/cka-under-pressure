# Maintainer notes

Not attendee-facing. Open decisions and things to review before publishing.

## Decisions needed from the author

1. **License.** MIT (`LICENSE`, copyright 2026 Chad Crowell) covers the whole repository,
   including the Markdown content. If you would rather license the written material
   separately (for example CC BY 4.0), add a content-license note and scope `LICENSE`
   to the scripts and manifests.
2. **Repository URL and QR code.** Both are on the takeaway sheet. The URL is
   `https://github.com/kubeskills/cka-under-pressure`; the QR image is
   `takeaway/qr-code-for-cka-under-pressure-talk-kubecon-na-2026.png` and decodes to that
   URL (checked with the macOS CoreImage detector). `tests/check_docs.py` requires both the
   URL and the image reference in the Markdown and HTML sheets, and allows no other URL there.
   If the repo ever moves, regenerate the QR code and update the URL in `check_docs.py`.
3. **Talk length.** Decided: the slot is 10 minutes and Part 7 stays in the runbook. No
   per-part timings are measured yet; rehearse against a stopwatch and re-time.
4. **Suggested timeboxes** in `tasks/*.md` (15/8 and 10/6 minutes) are unmeasured guesses.
   Pilot them with a few attendees and adjust.
5. **The repo's existing README.** `README.md` previously held only a title and one line
   ("KubeCon Tip Talk - KubeCon NA 2026"). It was replaced by the kit's README; the original
   is in git history (`git show HEAD:README.md`).
6. **Reference PDFs.** The book and curriculum PDFs live in the parent speaker workspace,
   outside this repository. The kit does **not** use or quote either file. Keep them out of
   the published repo.
7. **Branch and commit.** Nothing here has been staged or committed. Your convention is
   `feature/<change-name>` with conventional commits; create the branch when you are ready.

## Exam-claims policy

Exam facts (the test format and time limit, the pass mark, topic weightings, Kubernetes
version, allowed resources, proctoring rules) live **only** in `FAQ/cka-exam-faq.md`. Each answer there must end with
`Source (checked YYYY-MM-DD): <official Linux Foundation URL>`, and `tests/check_docs.py`
fails if a section asserts such a fact without that line. Outside `FAQ/` it always fails.
Everywhere else the kit links outward instead of asserting. Nothing in the kit promises a
pass or claims to reproduce the exam environment.

The FAQ was checked on 2026-11-04 against the official exam page, the CKA/CKAD/CKS FAQ and
the resources-allowed page. The pages were read through an automated fetch-and-summarize
tool, not by hand, so **re-read the three pages yourself before publishing or presenting**,
and refresh the dates when you re-verify. The Kubernetes version (v1.37) has been confirmed
by the author against the official source; the other facts have not been re-read by hand.

## Spoiler hygiene

- `lab/scenarios/variation-*/kustomization.yaml` contain the seeded faults and say so
  (`SPOILER`). The README tells attendees not to browse `lab/` before attempting a task.
- `scripts/reset.sh` discards `kubectl apply` output so setup does not list what exists.
- `tests/check_docs.py` fails if task briefs contain solution vocabulary (for example
  `targetPort`, `selector`, `readinessProbe`, or the solving commands).

## Keeping things in sync

| If you change… | Also update / re-run |
|---|---|
| Acceptance criteria text | `tasks/<id>.md` **and** `scripts/lib/verify.py` (`tests/check_docs.py` enforces exact matches) |
| The app image tag, or the kind node image | `lab/base/app-template/deployment.yaml` (app) or `lab/kind-cluster.yaml` (node); the verifier and scripts read them from there. Also update the image names in the `README.md` quickstart and download table (`tests/check_docs.py` enforces it). Re-run `tests/e2e.sh` |
| `takeaway/one-page.md` | `takeaway/one-page.html` (kept in sync by hand; a heading check exists) |
| Solutions | Commands in ` ```bash solution ` blocks are executed verbatim by `tests/e2e.sh` |
| Runbook demo commands | ` ```bash demo-mistake ` / ` demo-recover ` blocks are executed by `tests/e2e.sh` |

## Adding a scenario

1. `lab/scenarios/<id>/{kustomization.yaml,namespace.yaml}` (copy an existing one; set the
   `app.kubernetes.io/instance` label to the id).
2. Add `<id>` to `LAB_SCENARIOS` in `scripts/lib/common.sh`.
3. Add its criteria to `SCENARIOS` in `scripts/lib/verify.py`.
4. Add `tasks/<id>.md`, `hints/<id>/level-{1,2,3}.md`, `solutions/<id>.md`.
5. Add the id to the loops in `tests/e2e.sh`, then run `tests/run-static.sh`.

## Concurrency

The `drill-*` namespaces are shared state. Running two of `reset.sh`, `verify.sh`, or
`tests/e2e.sh` against the same cluster at once collides (observed during validation as
`AlreadyExists` errors). There is deliberately no locking; run one at a time.

## Known limitations

See `docs/validation-report.md` (“Known limitations” and “Untested assumptions”).

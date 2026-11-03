# Maintainer notes

Not attendee-facing. Open decisions and things to review before publishing.

## Decisions needed from the author

1. **License.** MIT (`LICENSE`, copyright 2026 Chad Crowell) covers the whole repository,
   including the Markdown content. If you would rather license the written material
   separately (for example CC BY 4.0), add a content-license note and scope `LICENSE`
   to the scripts and manifests.
2. **QR code.** The repository URL (`https://github.com/kubeskills/cka-under-pressure`) is
   filled in on the takeaway sheet. The QR code is still a `PLACEHOLDER` in
   `takeaway/one-page.md` and `takeaway/one-page.html`; replace both before printing.
   `tests/check_docs.py` requires that placeholder to remain until you drop that check, and
   allows no URL on the sheet other than the repo URL.
3. **Talk length.** The runbook is modular (core + one optional extension). Confirm the
   slot, then decide whether to keep Part 7.
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

The kit makes **no** claims about current exam requirements, domains, weights, versions,
allowed resources or rules. It links outward instead: the README links the official Linux
Foundation exam page and the Kubernetes docs. **Both URLs were copied from your own resource
list and were not fetched or re-verified by this build.** If you later add an exam claim,
verify it against the official Linux Foundation / CNCF source and record the URL and date
next to it. Nothing in the kit promises a pass or claims to reproduce the exam environment.

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
| The app image tag | Only `lab/base/app-template/deployment.yaml`; the verifier and scripts read it from there. Re-run `tests/e2e.sh` |
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

## Known limitations

See `docs/validation-report.md` (“Known limitations” and “Untested assumptions”).

# Presenter runbook — “CKA Under Pressure: A Better Way to Practice”

**Talk length:** not yet confirmed. This runbook is modular: the **core demo** (Parts 1–6)
stands alone; the **extension** (Part 7) is optional. Pacing notes are rough estimates,
not rehearsed timings. Re-time after a rehearsal.

**The point of the demo is the practice method, not kubectl speed.** Type slowly. Narrate
the *reading*, the *orienting*, and the *verifying*. If the audience remembers one thing:

> “Don’t practice until the exercise feels familiar. Practice until you can solve it
> without the walkthrough.”

Say this too, because it is easy to lose: **the timer is a diagnostic tool, not the goal
of every session.** Learn the skill first; add time pressure once the workflow is solid.

---

## Preflight checklist

### The day before (on a reliable network)

- [ ] `scripts/preflight.sh` passes.
- [ ] `scripts/cluster-up.sh` created the cluster (note: this downloads the node image if it is not cached).
- [ ] `scripts/reset.sh --all --yes` ran once. This downloads the app image (`busybox`) **into the cluster node**, so the demo does not depend on conference Wi‑Fi. The cache lives inside the node; deleting the cluster discards it.
- [ ] Rehearsed Parts 1–6 end to end at least once.
- [ ] Takeaway sheet: real repo URL and QR code substituted for the placeholders in `takeaway/one-page.html`, then printed and checked.
- [ ] (Optional) `tests/e2e.sh --yes` run against the lab cluster.

### 30 minutes before

- [ ] Docker is running; `scripts/preflight.sh` says the lab cluster is reachable and the app image is cached.
- [ ] `scripts/reset.sh --yes baseline` completed (this is the clean starting state).
- [ ] Sanity check: `scripts/verify.sh baseline` **fails** with exit code 1 (initial state is incomplete by design).
- [ ] Notifications off; battery/power connected.

### 5 minutes before

- [ ] Terminal prepared (below). A visible timer is ready *but not started*.
- [ ] `tasks/baseline.md` open in a second window or pane, large font.
- [ ] Fallback `presenter/sample-output.md` open in a tab, in case the live demo fails.

> The demo path is designed to need no network once the image is cached on the node.
> **That has not been tested with networking disabled**, so treat it as unverified.

## Terminal preparation

```bash
cd /path/to/cka-tip-talk
export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"
PS1='$ '
clear
```

- Font size large enough for the back row; window about 100 columns wide.
- Plain `kubectl` (no aliases) so the audience can follow every command.
- Your `~/.kube/config` is **not** used by this kit, so your other contexts cannot be hit
  by the lab scripts. Your own shell's `kubectl` still uses `KUBECONFIG` once exported, so
  open a fresh terminal for the demo.

---

## Core demo

### Part 1 — Frame the method (say; no typing)

**Say:** “Watching someone solve a Kubernetes problem isn’t the same as solving it
yourself. Here is a drill: no walkthrough, a clear outcome, and a check that tells me
whether I’m actually done. I’ll do it once, slowly, and I’m going to make a realistic
mistake on purpose.”

### Part 2 — Read

**Show** `tasks/baseline.md`. **Read the outcome and the acceptance criteria aloud.**
Underline (cursor/laser) the *constraints*: port 80, 3 replicas, `report` must stay intact.

**Say:** “Reading is the first skill. If I misread this, nothing after it matters.”

### Part 3 — Orient

**Type:**

```bash
kubectl config current-context
kubectl -n drill-baseline get deployment,pods
```

**Expect:** context `kind-cka-tip-talk`; Deployments `web` (1/1) and `report` (1/1); no Service.

**Say:** “Before I change anything: right cluster? Right namespace? What exists?”

### Part 4 — Solve (with the controlled mistake)

**Say:** “Smallest change that gets me toward the outcome. Scale it, then expose it.”

**Type** (this is the deliberate mistake; it is recoverable and runs entirely inside the lab namespace):

```bash demo-mistake
kubectl -n drill-baseline scale deployment web --replicas=3
kubectl -n drill-baseline expose deployment web --port=80
```

**Expect:** `deployment.apps/web scaled` and `service/web exposed`.

**Say:** “Both commands succeeded. Am I done?” *(Pause.)*

### Part 5 — Verify, and learn from the failure

**Type:**

```bash
scripts/verify.sh baseline; echo "exit code: $?"
```

**Expect (landmarks, not exact text):** a header saying *not official CKA scoring*; AC1 and
AC2 **PASS**; AC3 and AC4 **FAIL** (the requests don’t get through; the line names the
symptom, not the cause); AC5 **PASS**; `exit code: 1`.

> **Rehearse this once.** The expectation that `expose` without a target port produces a
> Service that points at the wrong port is the claim this demo rests on. It is recorded in
> `docs/validation-report.md` whether it held on the tested kubectl version.

**Say:** “Two commands succeeded and the task is not done. A successful command is not
proof. The check tests behavior: can a client in the namespace actually reach the app?”

**Review aloud** (this is the part people remember): “Where did I hesitate? What did I
assume? I assumed the Service port is the same as the application’s port. I never
checked what the application listens on.”

### Part 6 — Fix, re-verify, reset

**Type:**

```bash demo-recover
kubectl -n drill-baseline get deployment web -o jsonpath='{.spec.template.spec.containers[0].ports}{"\n"}'
kubectl -n drill-baseline patch service web --type merge -p '{"spec":{"ports":[{"port":80,"targetPort":8080}]}}'
```

```bash
scripts/verify.sh baseline; echo "exit code: $?"
```

**Expect:** the container port printed; then all five criteria **PASS**; `exit code: 0`.

**Say:** “Smallest justified change: one field on one object. Now the ladder:
learn it with no timer, attempt it alone, verify, review, repeat with a *variation*, and
only then add the timer. The timer exposes gaps; it doesn’t replace the workflow.”

**Reset** (so the lab is ready for the next demo or for questions):

```bash
scripts/reset.sh --yes baseline
```

**Close:** hold up the takeaway sheet; point at the kit; mention that the baseline is now
“familiar,” so attendees should do it again **without notes**, then try `variation-a` and
`variation-b`, which they haven’t seen.

---

## Optional extension — Part 7: a variation (`variation-a`)

Use this if time allows. It shows the same workflow on a *different* fault.

```bash
scripts/reset.sh --yes variation-a
```

1. **Read** `tasks/variation-a.md`; point out the constraint (“running Pods must not be restarted”).
2. **Predict:** ask the audience where they would look first. Don’t answer yet.
3. **Verify first, before solving:** `scripts/verify.sh variation-a`. Expect AC1 PASS but AC3/AC4 FAIL.
   Say: “Verifying *before* solving tells me what the actual gap is.”
4. **Diagnose:** `scripts/verify.sh --diagnose variation-a` prints read-only observations (labels, EndpointSlices). Let the audience spot the mismatch.
5. **Introduce the timer now**, visibly, as a diagnostic: “I understand the workflow, so now the clock shows me where I’m slow.” Fix it, re-verify.
6. **Avoid** presenting the solution as “the answer”; it is one valid fix (`solutions/variation-a.md`).

Reset afterwards: `scripts/reset.sh --yes variation-a`.

---

## Reset instructions

| Situation | Command |
|---|---|
| Back to the clean baseline | `scripts/reset.sh --yes baseline` |
| Reset everything | `scripts/reset.sh --yes --all` |
| Remove lab namespaces, keep the cluster | `scripts/clean.sh --yes` |
| Remove the cluster entirely | `scripts/cluster-down.sh --yes` |

`reset.sh` deletes and recreates only `drill-*` namespaces that carry the lab ownership label.

## If something goes wrong

| Symptom | What to do |
|---|---|
| `verify.sh` prints `ERROR` / exits 4 | The check couldn’t run (not your solution). Run `scripts/preflight.sh`; check Docker is running. |
| `scripts/*` exits 3 (“Refusing…”) | Wrong or missing lab kubeconfig/context. `export KUBECONFIG="$PWD/.kube/cka-tip-talk.kubeconfig"`. Nothing was changed. |
| Pods stuck `ImagePullBackOff` | The app image wasn’t cached and the network is down. Switch to the fallback below. |
| `expose` result differs from the runbook | The controlled mistake behaved differently on this kubectl version. Use the fallback; note it for the maintainer. |
| Cluster is gone / Docker restarted | `scripts/cluster-up.sh` then `scripts/reset.sh --yes baseline` (needs the image cached or network). |

## Fallback if the live environment fails

Open `presenter/sample-output.md` and narrate the same five beats (read, orient, solve,
verify, review) over the sample output. **Say out loud that it is sample output** and not a
live run. Do not present it as a captured result unless its header says it was captured, and
say which machine and date it was captured on.

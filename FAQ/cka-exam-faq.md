# CKA exam FAQ

Frequently asked questions about the Certified Kubernetes Administrator (CKA) exam.

**This kit does not set or define exam rules.** Every exam fact below was read from an
official Linux Foundation page on **2026-11-04**, and the page is named under the answer.
Exam details change (versions, score, rules, price), so **treat this file as a snapshot and
confirm on the official pages before you rely on it**:

- Exam page: <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>
- CKA/CKAD/CKS FAQ: <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>
- Resources allowed: <https://docs.linuxfoundation.org/tc-docs/certification/certification-resources-allowed>

Answers that are about this kit rather than the exam are in
[Questions about this kit](#questions-about-this-kit) and cite no source.

## About the exam

### What kind of exam is it?

An online, proctored, performance-based test: you solve multiple tasks from a command line
running Kubernetes. It is not multiple choice.

Source (checked 2026-11-04): <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>

### How long is it?

Candidates have 2 hours.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### What is the passing score?

A score of 66% or above must be earned to pass. Scoring is automatic, and the score report is
emailed within 24 hours of completing the exam, barring exceptions or technical difficulties.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### What topics does it cover, and how are they weighted?

The exam page lists these domains and weightings:

| Domain | Weight |
| --- | --- |
| Troubleshooting | 30% |
| Cluster Architecture, Installation & Configuration | 25% |
| Services & Networking | 20% |
| Workloads & Scheduling | 15% |
| Storage | 10% |

The authoritative breakdown is the curriculum document linked from the exam page. Read that,
not this table, when planning your study.

Source (checked 2026-11-04): <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>

### Which Kubernetes version is on the exam?

Kubernetes v1.37. Both official pages state it, and it has been confirmed independently.
Practice on the version the exam uses where you can, because behavior and `kubectl` defaults
change between releases.

Sources (checked 2026-11-04): <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/> and <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### Are there prerequisites?

The exam page states there are no prerequisites for the exam.

Source (checked 2026-11-04): <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>

### What if I don't pass?

The exam page lists one retake with the exam, and the FAQ says a retake is offered "when
eligible" to those who do not pass the first time, regardless of why. Neither page gives
details on waiting periods or limits, so read the current terms before you book.

Sources (checked 2026-11-04): <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/> and <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### How long is the certification valid?

Two years. Certifications achieved before April 01, 2024 were valid for three years. You can
renew by retaking and passing before the expiration date.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### How much does it cost?

The price and bundles change, so this file does not list them. See the exam page.

## During the exam

### Can I use the Kubernetes documentation?

Yes, within limits. In the browser inside the exam environment you may use:

- Kubernetes documentation (`kubernetes.io/docs`); site search is allowed, but you must not open
  external search results
- the Kubernetes blog (`kubernetes.io/blog`)
- Helm documentation (`helm.sh/docs`)
- Gateway API documentation (`gateway-api.sigs.k8s.io`), which applies to CKA only
- task-specific links shown in the exam's Quick Reference box

Resources must be used to work independently on exam tasks, not for third-party assistance or
research, and must be accessed from within the Linux server terminal the exam is delivered on.
The page also allows documents installed by the distribution under `/usr/share`, and
distribution packages. English docs are recommended as the most up to date.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/certification-resources-allowed>

### Can I bring notes or bookmarks, or use AI assistants?

The resources-allowed page does not address personal notes, bookmarks, a second device, scratch
paper, or AI assistants. When a rule is not stated, do not assume it is permitted: check the
current Candidate Handbook and the Linux Foundation's agreement, or ask the Linux Foundation,
before exam day.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/certification-resources-allowed>

### How is the exam proctored, and what do I need?

It is proctored remotely through PSI's Bridge platform using the PSI Secure Browser, and the
proctor can see all of your monitors. The FAQ lists these requirements:

- one active monitor ("Dual Monitors are NOT supported"); a 15" or larger screen at 1080p is recommended
- a working microphone and webcam, and a reliable internet connection that allows HTTPS to AWS S3 endpoints
- a personal device rather than a work-provided one
- no other applications or browser windows running
- a private, clutter-free room with the door closed
- a valid, unexpired, original government-issued photo ID whose first and last name exactly match the name on your exam checklist

Run PSI's system check ahead of time. This summary is not complete; the FAQ has the full list.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

### Is there an official practice simulator?

Registrants get access to a killer.sh exam simulator with two attempts, each active for 36
hours from activation. The FAQ notes it is not included in CKA-SINGLE registrations.

Source (checked 2026-11-04): <https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks>

## Questions about this kit

### Is this kit an exam question set, or does it copy the exam?

No. It is original practice material. It does not reproduce exam questions or the exam
environment, and `scripts/verify.sh` is a lab check written for this workshop, not official
scoring.

### Will completing the drills guarantee that I pass?

No. The drills practice a *method* (Read, Orient, Solve, Verify, Review). They do not cover
the exam's content, and nothing in this kit predicts a score.

### Should I practice against a timer?

Not at first. Learn the skill with no pressure, attempt it alone, verify, review your
mistakes, repeat with a variation, and only then add time pressure. The timer is a diagnostic
tool, not the goal of every session. See [`takeaway/one-page.md`](../takeaway/one-page.md).

### Can I use the hints and solutions while practicing?

Hints unlock in three levels (`hints/`), one level at a time, and only when you are stuck. The
solutions in `solutions/` spoil the tasks, so open them last. Anything that meets the
acceptance criteria counts as a valid solution.

### Why does the verifier test behavior instead of checking my commands?

Because a command that succeeds is not proof that the task is done. The verifier sends real
requests to the Service from inside the cluster. See the [README](../README.md).

### Does this kit touch my real clusters?

No. Scripts use a dedicated kind cluster named `cka-tip-talk` and a separate kubeconfig, pass
`--kubeconfig` and `--context` on every call, and refuse to act on any other cluster. See the
safety model in the [README](../README.md#safety-model).

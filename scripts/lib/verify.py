#!/usr/bin/env python3
"""Acceptance checks for the CKA Under Pressure lab.

These are lab checks written for this workshop. They are NOT official CKA scoring.

Run through scripts/verify.sh, which validates the kubeconfig/context first and
exports LAB_KUBECONFIG, LAB_CONTEXT and LAB_NAMESPACE. Every kubectl call made here
passes --kubeconfig and --context explicitly.

Exit codes: 0 all PASS, 1 at least one FAIL, 2 usage, 4 at least one ERROR
(the verifier or environment failed, so results cannot be trusted).

Temporary resources: one Pod named verify-probe-<hex> in the scenario namespace,
labelled app.kubernetes.io/component=verifier-probe. It is deleted before exit,
and stale probes from interrupted runs are swept at the start of each run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_ERROR = 4

PASS = "PASS"
FAIL = "FAIL"
ERROR = "ERROR"

REPO_ROOT = Path(__file__).resolve().parents[2]
OWNER_KEY = "app.kubernetes.io/managed-by"
OWNER_VALUE = "cka-under-pressure"
INSTANCE_KEY = "app.kubernetes.io/instance"
COMPONENT_KEY = "app.kubernetes.io/component"
PROBE_COMPONENT = "verifier-probe"

WEB_REPLICAS = 3
PROBE_REQUESTS = 12  # bounded sample; 3 replicas all landing on one Pod is ~1e-5
PROBE_MAX_FAILURES = 3  # stop early so a dead Service costs seconds, not a minute
PROBE_REQUEST_TIMEOUT = 2  # seconds per request inside the probe
READY_GRACE_SECONDS = 10
PROBE_START_TIMEOUT = 60
KUBECTL_TIMEOUT = 30


class VerifierError(Exception):
    """The verifier or environment failed; the criterion could not be judged."""


# --------------------------------------------------------------------------- kubectl


class Kubectl:
    """Thin kubectl wrapper that pins kubeconfig/context and bounds every call."""

    def __init__(self, kubeconfig: str, context: str, request_timeout: int = 15):
        self.kubeconfig = kubeconfig
        self.context = context
        self.request_timeout = request_timeout

    def run(
        self,
        args: Sequence[str],
        timeout: int = KUBECTL_TIMEOUT,
        input_text: Optional[str] = None,
        request_timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        per_request = request_timeout
        if per_request is None:
            per_request = self.request_timeout
        cmd = [
            "kubectl",
            "--kubeconfig",
            self.kubeconfig,
            "--context",
            self.context,
            f"--request-timeout={per_request}s",
            *args,
        ]
        try:
            return subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VerifierError(
                f"kubectl {' '.join(args[:3])} timed out after {timeout}s"
            ) from exc
        except FileNotFoundError as exc:
            raise VerifierError("kubectl not found on PATH") from exc

    def get_json(self, args: Sequence[str]) -> Optional[dict]:
        """Return parsed JSON, or None when the object does not exist."""
        proc = self.run(["get", *args, "-o", "json"])
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout)
            except ValueError as exc:
                raise VerifierError(f"kubectl get {' '.join(args)}: bad JSON") from exc
        if "NotFound" in proc.stderr:
            return None
        raise VerifierError(
            f"kubectl get {' '.join(args)} failed: {proc.stderr.strip()}"
        )


# ----------------------------------------------------------------------- probe sample


@dataclass
class ProbeSample:
    attempted: int = 0
    failures: int = 0
    responses: List[Tuple[str, str]] = field(default_factory=list)  # (app, pod)
    last_error: str = ""


RESPONSE_RE = re.compile(r"^OK app=(\S+) pod=(\S+)\s*$")


def classify_error(text: str) -> str:
    """Name the symptom of a failed request without hinting at a cause or fix."""
    lowered = text.lower()
    if "bad address" in lowered:
        return "the Service name did not resolve"
    if "refused" in lowered:
        return "connection refused"
    if "timed out" in lowered or "timeout" in lowered:
        return "connection timed out"
    if "server returned error" in lowered:
        return "the server returned an HTTP error"
    return "request failed" if not text else f"request failed ({text.strip()[:80]})"


def parse_probe_output(output: str) -> ProbeSample:
    sample = ProbeSample()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("DIAG"):
            sample.last_error = classify_error(line[4:].strip())
            continue
        if not line:
            continue
        sample.attempted += 1
        match = RESPONSE_RE.match(line)
        if match:
            sample.responses.append((match.group(1), match.group(2)))
        else:
            sample.failures += 1
    if sample.failures and not sample.last_error:
        sample.last_error = "request failed"
    return sample


class Probe:
    """Short-lived in-cluster client Pod: tests the Service like a real client."""

    def __init__(self, kubectl: Kubectl, namespace: str, image: str, sleep=time.sleep):
        self.kubectl = kubectl
        self.namespace = namespace
        self.image = image
        self.sleep = sleep
        self.name = f"verify-probe-{uuid.uuid4().hex[:8]}"
        self.created = False

    def manifest(self) -> dict:
        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace,
                "labels": {OWNER_KEY: OWNER_VALUE, COMPONENT_KEY: PROBE_COMPONENT},
            },
            "spec": {
                "restartPolicy": "Never",
                "terminationGracePeriodSeconds": 0,
                # Backstop: even if cleanup is skipped, the probe stops on its own.
                "activeDeadlineSeconds": 300,
                "automountServiceAccountToken": False,
                "securityContext": {
                    "runAsNonRoot": True,
                    "runAsUser": 65534,
                    "runAsGroup": 65534,
                    "seccompProfile": {"type": "RuntimeDefault"},
                },
                "containers": [
                    {
                        "name": "probe",
                        "image": self.image,
                        "command": ["sleep", "300"],
                        "resources": {
                            "requests": {"cpu": "5m", "memory": "8Mi"},
                            "limits": {"cpu": "50m", "memory": "32Mi"},
                        },
                        "securityContext": {
                            "allowPrivilegeEscalation": False,
                            "readOnlyRootFilesystem": True,
                            "capabilities": {"drop": ["ALL"]},
                        },
                    }
                ],
            },
        }

    def __enter__(self) -> "Probe":
        self._sweep_stale()
        proc = self.kubectl.run(
            ["create", "-n", self.namespace, "-f", "-"],
            input_text=json.dumps(self.manifest()),
        )
        if proc.returncode != 0:
            raise VerifierError(f"could not create probe Pod: {proc.stderr.strip()}")
        self.created = True
        self._wait_running()
        return self

    def __exit__(self, *exc_info) -> None:
        self.cleanup()

    def _selector(self) -> str:
        return f"{OWNER_KEY}={OWNER_VALUE},{COMPONENT_KEY}={PROBE_COMPONENT}"

    def _sweep_stale(self) -> None:
        # Only Pods carrying both of our labels are ever deleted.
        self.kubectl.run(
            [
                "delete",
                "pods",
                "-n",
                self.namespace,
                "-l",
                self._selector(),
                "--ignore-not-found",
                "--wait=true",
                "--timeout=30s",
            ],
            timeout=45,
        )

    def _wait_running(self) -> None:
        deadline = time.monotonic() + PROBE_START_TIMEOUT
        while True:
            pod = self.kubectl.get_json(["pod", self.name, "-n", self.namespace])
            if pod is None:
                raise VerifierError("probe Pod disappeared before it started")
            status = pod.get("status", {})
            phase = status.get("phase", "")
            if phase == "Running":
                return
            if phase in ("Failed", "Succeeded"):
                raise VerifierError(f"probe Pod ended early (phase {phase})")
            for cs in status.get("containerStatuses", []):
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting.get("reason") in (
                    "ErrImagePull",
                    "ImagePullBackOff",
                    "InvalidImageName",
                ):
                    raise VerifierError(
                        f"probe image {self.image} could not be pulled "
                        f"({waiting['reason']}); check network access"
                    )
            if time.monotonic() > deadline:
                raise VerifierError(
                    f"probe Pod not Running after {PROBE_START_TIMEOUT}s "
                    f"(phase {phase})"
                )
            self.sleep(1)

    def sample(self, url: str) -> ProbeSample:
        script = (
            f'URL="{url}"; i=0; f=0; '
            f'while [ "$i" -lt {PROBE_REQUESTS} ]; do '
            f'if out=$(wget -q -T {PROBE_REQUEST_TIMEOUT} -O - "$URL" 2>/dev/null); '
            'then echo "OK $out"; '
            "else f=$((f+1)); echo ERR; "
            f'[ "$f" -ge {PROBE_MAX_FAILURES} ] && break; fi; '
            "i=$((i+1)); done; "
            'if [ "$f" -gt 0 ]; then '
            f'echo "DIAG $(wget -q -T {PROBE_REQUEST_TIMEOUT} -O - "$URL" '
            '2>&1 >/dev/null | tail -n 1)"; fi'
        )
        budget = PROBE_REQUESTS * (PROBE_REQUEST_TIMEOUT + 1) + 15
        proc = self.kubectl.run(
            ["exec", "-n", self.namespace, self.name, "--", "sh", "-c", script],
            timeout=budget,
            request_timeout=0,
        )
        if proc.returncode != 0 and not proc.stdout.strip():
            raise VerifierError(f"probe exec failed: {proc.stderr.strip()}")
        return parse_probe_output(proc.stdout)

    def cleanup(self) -> None:
        if not self.created:
            return
        try:
            self.kubectl.run(
                [
                    "delete",
                    "pod",
                    self.name,
                    "-n",
                    self.namespace,
                    "--ignore-not-found",
                    "--wait=true",
                    "--timeout=30s",
                ],
                timeout=45,
            )
            self.created = False
        except VerifierError as exc:
            print(
                f"WARN: could not delete probe Pod {self.name}: {exc}. "
                f"Remove it with: kubectl -n {self.namespace} delete pod {self.name}",
                file=sys.stderr,
            )


# ------------------------------------------------------------------------------- lab


@dataclass
class Result:
    status: str
    detail: str = ""


@dataclass
class Lab:
    kubectl: Kubectl
    scenario: str
    namespace: str
    app_image: str
    grace: int = READY_GRACE_SECONDS
    sleep: Callable[[float], None] = time.sleep
    _sample: Optional[ProbeSample] = None
    _sample_error: Optional[VerifierError] = None

    def fetch(self, kind: str, name: str) -> Optional[dict]:
        return self.kubectl.get_json([kind, name, "-n", self.namespace])

    def service_url(self) -> str:
        return f"http://web.{self.namespace}.svc:80/"

    def sample(self) -> ProbeSample:
        """Probe the Service once per run; the probe Pod is removed immediately.

        A probe failure is remembered, so later criteria report the same ERROR
        instead of repeating a slow attempt.
        """
        if self._sample_error is not None:
            raise self._sample_error
        if self._sample is None:
            try:
                with Probe(
                    self.kubectl, self.namespace, self.app_image, self.sleep
                ) as probe:
                    self._sample = probe.sample(self.service_url())
            except VerifierError as exc:
                self._sample_error = exc
                raise
        return self._sample

    def web_pod_names(self) -> List[str]:
        web = self.fetch("deployment", "web")
        if web is None:
            return []
        labels = web["spec"]["selector"].get("matchLabels", {})
        selector = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        pods = self.kubectl.get_json(["pods", "-n", self.namespace, "-l", selector])
        items = (pods or {}).get("items", [])
        return [
            p["metadata"]["name"]
            for p in items
            if not p["metadata"].get("deletionTimestamp")
        ]


# ------------------------------------------------------------------------- criteria


def check_web_ready(lab: Lab) -> Result:
    deadline = time.monotonic() + lab.grace
    while True:
        web = lab.fetch("deployment", "web")
        if web is None:
            return Result(FAIL, "Deployment 'web' not found")
        wanted = web["spec"].get("replicas", 1)
        status = web.get("status", {})
        ready = status.get("readyReplicas", 0)
        available = status.get("availableReplicas", 0)
        if wanted != WEB_REPLICAS:
            return Result(FAIL, f"Deployment 'web' has {wanted} replica(s) configured")
        if ready >= WEB_REPLICAS and available >= WEB_REPLICAS:
            return Result(PASS, f"{ready}/{wanted} Pods Ready")
        if time.monotonic() >= deadline:
            return Result(
                FAIL, f"{ready}/{wanted} Pods Ready after waiting {lab.grace}s"
            )
        lab.sleep(2)


def check_service(lab: Lab) -> Result:
    svc = lab.fetch("service", "web")
    if svc is None:
        return Result(FAIL, "Service 'web' not found")
    spec = svc["spec"]
    svc_type = spec.get("type", "ClusterIP")
    ports = [p.get("port") for p in spec.get("ports", [])]
    if svc_type != "ClusterIP":
        return Result(FAIL, f"Service 'web' is type {svc_type}")
    if 80 not in ports:
        return Result(FAIL, f"Service 'web' exposes port(s) {ports}; 80 is required")
    return Result(PASS, "ClusterIP, port 80")


def check_reachable(lab: Lab) -> Result:
    sample = lab.sample()
    ok = len(sample.responses)
    tally = f"{ok}/{sample.attempted} requests to {lab.service_url()}"
    if sample.failures or ok == 0:
        reason = sample.last_error or "no responses"
        return Result(FAIL, f"{tally} succeeded; {reason}")
    return Result(PASS, f"{tally} answered")


def check_only_web(lab: Lab) -> Result:
    sample = lab.sample()
    if not sample.responses:
        return Result(FAIL, "not evaluated: no successful responses")
    apps = sorted({app for app, _ in sample.responses})
    if apps != ["web"]:
        return Result(FAIL, f"responses came from application(s): {', '.join(apps)}")
    answering = {pod for _, pod in sample.responses}
    strays = sorted(answering - set(lab.web_pod_names()))
    if strays:
        return Result(
            FAIL, f"answered by Pod(s) outside Deployment 'web': {', '.join(strays)}"
        )
    if len(answering) < 2:
        return Result(
            FAIL,
            f"only {len(answering)} distinct Pod answered {sample.attempted} requests",
        )
    return Result(PASS, f"{len(answering)} distinct web Pods answered")


def check_protected(lab: Lab) -> Result:
    problems: List[str] = []
    report = lab.fetch("deployment", "report")
    if report is None:
        problems.append("Deployment 'report' is missing")
    else:
        rstatus = report.get("status", {})
        image = report["spec"]["template"]["spec"]["containers"][0].get("image")
        if report["spec"].get("replicas") != 1 or rstatus.get("readyReplicas") != 1:
            problems.append("Deployment 'report' is not at 1/1 Ready")
        if image != lab.app_image:
            problems.append("Deployment 'report' image was changed")
    web = lab.fetch("deployment", "web")
    if web is not None:
        image = web["spec"]["template"]["spec"]["containers"][0].get("image")
        if image != lab.app_image:
            problems.append("Deployment 'web' image was changed")
    if lab.fetch("networkpolicy", "allow-same-namespace") is None:
        problems.append("NetworkPolicy 'allow-same-namespace' is missing")
    if problems:
        return Result(FAIL, "; ".join(problems))
    return Result(PASS, "report, web image, and NetworkPolicy unchanged")


def check_web_unmodified(lab: Lab) -> Result:
    web = lab.fetch("deployment", "web")
    if web is None:
        return Result(FAIL, "Deployment 'web' not found")
    generation = web["metadata"].get("generation")
    if generation != 1:
        return Result(
            FAIL,
            f"Deployment 'web' spec was modified (generation {generation}); "
            "its live Pods were restarted or replaced",
        )
    return Result(PASS, "Deployment 'web' spec unmodified (generation 1)")


def check_health_gating(lab: Lab) -> Result:
    web = lab.fetch("deployment", "web")
    if web is None:
        return Result(FAIL, "Deployment 'web' not found")
    container = web["spec"]["template"]["spec"]["containers"][0]
    if not container.get("readinessProbe"):
        return Result(FAIL, "the 'web' container has no readiness check")
    svc = lab.fetch("service", "web")
    if svc is not None and svc["spec"].get("publishNotReadyAddresses"):
        return Result(FAIL, "Service 'web' sends traffic to Pods that are not Ready")
    return Result(PASS, "readiness check present; only Ready Pods receive traffic")


@dataclass(frozen=True)
class Criterion:
    id: str
    title: str  # must match the criterion text in tasks/<scenario>.md exactly
    check: Callable[[Lab], Result]


T_WEB_READY = "Deployment `web` has 3 replicas, all Ready"
T_SERVICE = "Service `web` is type ClusterIP and exposes port 80"
T_REACH = "Requests to the Service on port 80 from inside the namespace succeed"
T_ONLY_WEB = "Only `web` Pods answer, and more than one of them does"
T_PROTECTED = (
    "Protected resources are intact (`report`, the `web` image, NetworkPolicy)"
)
T_SERVICE_NAMED = "A Service named `web` exists, type ClusterIP, port 80"

SCENARIOS: Dict[str, List[Criterion]] = {
    "baseline": [
        Criterion("AC1", T_WEB_READY, check_web_ready),
        Criterion("AC2", T_SERVICE_NAMED, check_service),
        Criterion("AC3", T_REACH, check_reachable),
        Criterion("AC4", T_ONLY_WEB, check_only_web),
        Criterion("AC5", T_PROTECTED, check_protected),
    ],
    "variation-a": [
        Criterion("AC1", T_WEB_READY, check_web_ready),
        Criterion("AC2", T_SERVICE, check_service),
        Criterion("AC3", T_REACH, check_reachable),
        Criterion("AC4", T_ONLY_WEB, check_only_web),
        Criterion(
            "AC5",
            "The live `web` Pods were not restarted or replaced",
            check_web_unmodified,
        ),
        Criterion("AC6", T_PROTECTED, check_protected),
    ],
    "variation-b": [
        Criterion("AC1", T_WEB_READY, check_web_ready),
        Criterion("AC2", T_SERVICE, check_service),
        Criterion(
            "AC3",
            "Health checking on the `web` container is still in place",
            check_health_gating,
        ),
        Criterion("AC4", T_REACH, check_reachable),
        Criterion("AC5", T_ONLY_WEB, check_only_web),
        Criterion("AC6", T_PROTECTED, check_protected),
    ],
}


# ------------------------------------------------------------------------ runner


def read_app_image(root: Path = REPO_ROOT) -> str:
    """The image pin lives in one place: the app template manifest."""
    template = root / "lab" / "base" / "app-template" / "deployment.yaml"
    try:
        for line in template.read_text().splitlines():
            match = re.match(r"\s*image:\s*(\S+)\s*$", line)
            if match:
                return match.group(1)
    except OSError as exc:
        raise VerifierError(f"cannot read {template}: {exc}") from exc
    raise VerifierError(f"no image found in {template}")


def check_environment(lab: Lab) -> None:
    """Environment problems are ERRORs, never silent FAILs."""
    ns = lab.kubectl.get_json(["namespace", lab.namespace])
    if ns is None:
        raise VerifierError(
            f"namespace '{lab.namespace}' does not exist; "
            f"run: scripts/reset.sh {lab.scenario}"
        )
    labels = ns["metadata"].get("labels", {})
    if labels.get(OWNER_KEY) != OWNER_VALUE:
        raise VerifierError(f"namespace '{lab.namespace}' is not owned by this lab")
    if labels.get(INSTANCE_KEY) != lab.scenario:
        raise VerifierError(
            f"namespace '{lab.namespace}' belongs to scenario "
            f"'{labels.get(INSTANCE_KEY)}', not '{lab.scenario}'"
        )


def run_criteria(
    lab: Lab, criteria: Sequence[Criterion]
) -> List[Tuple[Criterion, Result]]:
    results = []
    for criterion in criteria:
        try:
            result = criterion.check(lab)
        except VerifierError as exc:
            result = Result(ERROR, str(exc))
        results.append((criterion, result))
    return results


def exit_code(results: Sequence[Tuple[Criterion, Result]]) -> int:
    statuses = {r.status for _, r in results}
    if ERROR in statuses:
        return EXIT_ERROR
    if FAIL in statuses:
        return EXIT_FAIL
    return EXIT_PASS


def diagnose(lab: Lab, out=None) -> None:
    """Read-only observations. Deliberately no analysis and no suggested fix."""
    out = out or sys.stdout
    print("\nDiagnostics (read-only observations; no advice)", file=out)
    commands = [
        (
            "Workloads",
            [
                "get",
                "deployments,pods,services,endpointslices",
                "-n",
                lab.namespace,
                "-o",
                "wide",
                "--show-labels",
            ],
        ),
        (
            "Recent events",
            ["get", "events", "-n", lab.namespace, "--sort-by=.lastTimestamp"],
        ),
    ]
    for title, args in commands:
        print(f"\n--- {title}", file=out)
        try:
            proc = lab.kubectl.run(args)
            text = proc.stdout if proc.returncode == 0 else proc.stderr
            print(text.rstrip() or "(none)", file=out)
        except VerifierError as exc:
            print(f"(unavailable: {exc})", file=out)


def render(
    lab: Lab,
    results: Sequence[Tuple[Criterion, Result]],
    context: str,
    out=None,
) -> None:
    out = out or sys.stdout
    color = out.isatty() and "NO_COLOR" not in os.environ
    palette = {PASS: "\033[32m", FAIL: "\033[31m", ERROR: "\033[33m"}

    def paint(status: str) -> str:
        text = f"{status:<5}"
        return f"{palette[status]}{text}\033[0m" if color else text

    print("CKA Under Pressure lab check (not official CKA scoring)", file=out)
    print(
        f"Scenario: {lab.scenario}   Context: {context}   Namespace: {lab.namespace}\n",
        file=out,
    )
    for criterion, result in results:
        print(f"  {paint(result.status)} {criterion.id}  {criterion.title}", file=out)
        if result.status != PASS and result.detail:
            print(f"        -> {result.detail}", file=out)
    counts = {
        s: sum(1 for _, r in results if r.status == s) for s in (PASS, FAIL, ERROR)
    }
    print(
        f"\nResult: {counts[PASS]} passed, {counts[FAIL]} failed, "
        f"{counts[ERROR]} error(s)",
        file=out,
    )
    if counts[ERROR]:
        print(
            "ERROR means the check itself could not run (environment/verifier), "
            "not that your solution is wrong. Try: scripts/preflight.sh",
            file=out,
        )


def main(
    argv: Optional[Sequence[str]] = None, kubectl: Optional[Kubectl] = None
) -> int:
    parser = argparse.ArgumentParser(description="CKA Under Pressure lab checks")
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--grace", type=int, default=READY_GRACE_SECONDS)
    args = parser.parse_args(argv)

    if kubectl is None:
        names = ("LAB_KUBECONFIG", "LAB_CONTEXT", "LAB_NAMESPACE")
        env = {k: os.environ.get(k, "") for k in names}
        if not all(env.values()):
            print(
                "ERROR: run this through scripts/verify.sh, "
                "which validates the context first.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        kubectl = Kubectl(env["LAB_KUBECONFIG"], env["LAB_CONTEXT"])
        namespace = env["LAB_NAMESPACE"]
    else:
        namespace = os.environ.get("LAB_NAMESPACE", f"drill-{args.scenario}")

    def _terminate(signum, _frame):  # let `with Probe` run its cleanup
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, _terminate)

    try:
        lab = Lab(
            kubectl=kubectl,
            scenario=args.scenario,
            namespace=namespace,
            app_image=read_app_image(),
            grace=args.grace,
        )
        check_environment(lab)
    except VerifierError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR

    results = run_criteria(lab, SCENARIOS[args.scenario])
    render(lab, results, kubectl.context)
    if args.diagnose:
        diagnose(lab)
    return exit_code(results)


if __name__ == "__main__":
    sys.exit(main())

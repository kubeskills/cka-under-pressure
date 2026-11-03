#!/usr/bin/env python3
"""Checks the rendered lab manifests against the lab's rules. No cluster needed.

Renders each scenario locally with `kubectl kustomize` (KUBECONFIG is pointed at
/dev/null to prove no cluster is contacted) and applies line-based checks. The checks
are regex-based, not a YAML parser, so they are a guard rail and not a full validator.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ["baseline", "variation-a", "variation-b"]
OWNER = "app.kubernetes.io/managed-by: cka-under-pressure"

failures = []
passes = 0


def check(ok, message):
    global passes
    if ok:
        passes += 1
    else:
        failures.append(message)
        print(f"FAIL: {message}")


def render(scenario):
    env = dict(os.environ, KUBECONFIG="/dev/null")
    proc = subprocess.run(
        ["kubectl", "kustomize", str(ROOT / "lab" / "scenarios" / scenario)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    check(proc.returncode == 0, f"{scenario}: kubectl kustomize failed: {proc.stderr.strip()}")
    return proc.stdout


def docs(rendered):
    return [d for d in re.split(r"^---\s*$", rendered, flags=re.M) if d.strip()]


def kind_of(doc):
    return re.search(r"^kind: (\S+)", doc, re.M).group(1)


def name_of(doc):
    return re.search(r"^  name: (\S+)", doc, re.M).group(1)


FORBIDDEN = [
    r"privileged: true",
    r"hostPath",
    r"hostNetwork: true",
    r"hostPID: true",
    r"hostIPC: true",
    r"kind: ClusterRole",
    r"kind: ClusterRoleBinding",
    r"cluster-admin",
    r"type: LoadBalancer",
    r"type: NodePort",
    r"kind: Ingress",
]

for scenario in SCENARIOS:
    out = render(scenario)
    parts = docs(out)
    kinds = sorted((kind_of(d), name_of(d)) for d in parts)
    expected = [
        ("Deployment", "report"),
        ("Deployment", "web"),
        ("Namespace", f"drill-{scenario}"),
        ("NetworkPolicy", "allow-same-namespace"),
    ]
    if scenario != "baseline":
        expected.append(("Service", "web"))
    check(kinds == sorted(expected), f"{scenario}: unexpected resources {kinds}")

    for pattern in FORBIDDEN:
        check(not re.search(pattern, out), f"{scenario}: forbidden construct /{pattern}/")

    for doc in parts:
        kind, name = kind_of(doc), name_of(doc)
        label = f"{scenario}/{kind}/{name}"
        check(OWNER in doc, f"{label}: missing ownership label")
        if kind != "Namespace":
            check(f"namespace: drill-{scenario}" in doc, f"{label}: not in drill-{scenario}")
        if kind == "Deployment":
            check("requests:" in doc and "limits:" in doc, f"{label}: resources requests/limits required")
            check("runAsNonRoot: true" in doc, f"{label}: runAsNonRoot required")
            check("allowPrivilegeEscalation: false" in doc, f"{label}: allowPrivilegeEscalation must be false")
            images = re.findall(r"image: (\S+)", doc)
            check(
                images and all(re.fullmatch(r"[\w./-]+:[\w.-]+", i) and not i.endswith(":latest") for i in images),
                f"{label}: image must be pinned to a specific tag: {images}",
            )
        if kind == "Namespace":
            check(f"app.kubernetes.io/instance: {scenario}" in doc, f"{label}: instance label must equal the scenario id")

    # The seeded starting state each doc/solution/verifier assumes.
    web = next(d for d in parts if kind_of(d) == "Deployment" and name_of(d) == "web")
    report = next(d for d in parts if kind_of(d) == "Deployment" and name_of(d) == "report")
    check("replicas: 1" in report, f"{scenario}: report must have 1 replica")
    if scenario == "baseline":
        check("replicas: 1" in web, "baseline: web must start at 1 replica")
        check(not any(kind_of(d) == "Service" for d in parts), "baseline: must start with no Service")
    else:
        check("replicas: 3" in web, f"{scenario}: web must have 3 replicas")
    if scenario == "variation-a":
        svc = next(d for d in parts if kind_of(d) == "Service")
        check(re.search(r"selector:\n    app: web\n", svc) is not None, "variation-a: Service selector fault missing")
        check("path: /healthz" in web, "variation-a: web readiness path must be healthy")
    if scenario == "variation-b":
        svc = next(d for d in parts if kind_of(d) == "Service")
        check("app.kubernetes.io/name: web" in svc, "variation-b: Service selector must be correct")
        check("path: /ready" in web, "variation-b: seeded readiness fault missing")

# Lab cluster definition: pinned, no host exposure.
kind_cfg = (ROOT / "lab" / "kind-cluster.yaml").read_text()
check(re.search(r"image: kindest/node:v[\d.]+@sha256:[0-9a-f]{64}", kind_cfg) is not None, "kind node image must be pinned by tag and digest")
for pattern in ("extraMounts", "extraPortMappings", "hostPath"):
    check(pattern not in kind_cfg, f"kind config must not use {pattern}")

# Single source of truth for the app image: template only.
template = (ROOT / "lab" / "base" / "app-template" / "deployment.yaml").read_text()
check(len(re.findall(r"image: ", template)) == 1, "app template must define exactly one image")

print(f"manifest checks: {passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)

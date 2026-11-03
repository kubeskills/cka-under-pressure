#!/usr/bin/env python3
"""Unit tests for scripts/lib/verify.py. No cluster, network, or kubectl needed.

Run: python3 -m unittest discover -s tests -p 'test_verify.py' -v
"""

import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "lib"))
import verify  # noqa: E402

IMAGE = verify.read_app_image()
NOT_FOUND = 'Error from server (NotFound): "x" not found'


def done(args, rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, rc, stdout, stderr)


def namespace(scenario, owned=True):
    labels = {verify.INSTANCE_KEY: scenario}
    if owned:
        labels[verify.OWNER_KEY] = verify.OWNER_VALUE
    return {"metadata": {"name": f"drill-{scenario}", "labels": labels}}


def deployment(
    name, replicas, ready, image=IMAGE, generation=1, readiness=True, selector=None
):
    container = {"name": name, "image": image}
    if readiness:
        container["readinessProbe"] = {"httpGet": {"path": "/healthz", "port": "http"}}
    return {
        "metadata": {"name": name, "generation": generation},
        "spec": {
            "replicas": replicas,
            "selector": {
                "matchLabels": selector or {"app.kubernetes.io/name": name},
            },
            "template": {"spec": {"containers": [container]}},
        },
        "status": {"readyReplicas": ready, "availableReplicas": ready},
    }


def service(port=80, svc_type="ClusterIP", publish_not_ready=False):
    spec = {"type": svc_type, "ports": [{"port": port}]}
    if publish_not_ready:
        spec["publishNotReadyAddresses"] = True
    return {"metadata": {"name": "web"}, "spec": spec}


def ok_lines(pods, app="web", n=12):
    return "\n".join(f"OK app={app} pod={pods[i % len(pods)]}" for i in range(n))


class FakeKubectl(verify.Kubectl):
    """Answers kubectl calls from an in-memory dict and records every call."""

    def __init__(self, objects, web_pods=(), probe_output="", exec_error=None):
        super().__init__("/fake/kubeconfig", "kind-fake")
        self.objects = objects
        self.web_pods = list(web_pods)
        self.probe_output = probe_output
        self.exec_error = exec_error
        self.error_for = {}
        self.calls = []
        self.probe_name = None
        self.probe_manifest = None

    def run(self, args, timeout=30, input_text=None, request_timeout=None):
        args = list(args)
        self.calls.append(args)
        verb = args[0]
        if verb == "get":
            return self._get(args)
        if verb == "create":
            self.probe_manifest = json.loads(input_text)
            self.probe_name = self.probe_manifest["metadata"]["name"]
            return done(args)
        if verb == "exec":
            if self.exec_error:
                raise verify.VerifierError(self.exec_error)
            return done(args, stdout=self.probe_output)
        return done(args)

    def _get(self, args):
        kind = args[1]
        if kind == "pods":
            items = [{"metadata": {"name": n}} for n in self.web_pods]
            return done(args, stdout=json.dumps({"items": items}))
        key = (kind, args[2])
        if kind == "pod" and args[2] == self.probe_name:
            pod = {"status": {"phase": "Running"}}
            return done(args, stdout=json.dumps(pod))
        if key in self.error_for:
            return done(args, rc=1, stderr=self.error_for[key])
        if key in self.objects:
            return done(args, stdout=json.dumps(self.objects[key]))
        return done(args, rc=1, stderr=NOT_FOUND)

    def verbs(self):
        return [c[0] for c in self.calls]


def lab_objects(scenario, **overrides):
    """A healthy, fully solved namespace; tests override pieces."""
    objs = {
        ("namespace", f"drill-{scenario}"): namespace(scenario),
        ("deployment", "web"): deployment(
            "web", 3, 3, selector={"app.kubernetes.io/name": "web"}
        ),
        ("deployment", "report"): deployment("report", 1, 1),
        ("service", "web"): service(),
        ("networkpolicy", "allow-same-namespace"): {"metadata": {"name": "x"}},
    }
    objs.update(overrides)
    return objs


WEB_PODS = ["web-a", "web-b", "web-c"]


def run_main(scenario, fake):
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with mock.patch.object(verify.time, "sleep"):
            code = verify.main(["--grace", "0", scenario], kubectl=fake)
    return code, out.getvalue(), err.getvalue()


def statuses(text):
    found = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > 2 and parts[1].startswith("AC") and parts[0] in (
            "PASS",
            "FAIL",
            "ERROR",
        ):
            found[parts[1]] = parts[0]
    return found


class BaselineTests(unittest.TestCase):
    def test_initial_state_fails_without_error(self):
        objs = lab_objects("baseline")
        objs[("deployment", "web")] = deployment("web", 1, 1)
        del objs[("service", "web")]
        fake = FakeKubectl(
            objs,
            web_pods=["web-a"],
            probe_output="ERR\nERR\nERR\nDIAG wget: bad address 'web.x.svc'",
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertEqual(
            statuses(out),
            {"AC1": "FAIL", "AC2": "FAIL", "AC3": "FAIL", "AC4": "FAIL", "AC5": "PASS"},
        )
        self.assertIn("the Service name did not resolve", out)

    def test_solved_state_passes(self):
        fake = FakeKubectl(
            lab_objects("baseline"),
            web_pods=WEB_PODS,
            probe_output=ok_lines(WEB_PODS),
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_PASS, out)
        self.assertEqual(set(statuses(out).values()), {"PASS"})

    def test_repeat_runs_give_the_same_result_and_leave_no_probe(self):
        for _ in range(2):
            fake = FakeKubectl(
                lab_objects("baseline"),
                web_pods=WEB_PODS,
                probe_output=ok_lines(WEB_PODS),
            )
            code, _, _ = run_main("baseline", fake)
            self.assertEqual(code, verify.EXIT_PASS)
            deletes = [c for c in fake.calls if c[0] == "delete"]
            self.assertIn(
                ["delete", "pod", fake.probe_name],
                [c[:3] for c in deletes],
                "probe Pod must be deleted before exit",
            )

    def test_connection_refused_is_named_without_hinting_a_cause(self):
        fake = FakeKubectl(
            lab_objects("baseline"),
            web_pods=WEB_PODS,
            probe_output="ERR\nERR\nERR\nDIAG wget: can't connect: Connection refused",
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertIn("connection refused", out)
        for word in ("targetPort", "selector", "endpoints"):
            self.assertNotIn(word, out)

    def test_traffic_reaching_report_fails_only_web_criterion(self):
        lines = ok_lines(["web-a", "web-b"], n=6) + "\n" + ok_lines(["r-1"], "report", 6)
        fake = FakeKubectl(
            lab_objects("baseline"), web_pods=WEB_PODS, probe_output=lines
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertEqual(statuses(out)["AC4"], "FAIL")
        self.assertEqual(statuses(out)["AC3"], "PASS")
        self.assertIn("report", out)

    def test_single_answering_pod_fails(self):
        fake = FakeKubectl(
            lab_objects("baseline"),
            web_pods=WEB_PODS,
            probe_output=ok_lines(["web-a"]),
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertEqual(statuses(out)["AC4"], "FAIL")

    def test_pod_outside_the_deployment_fails(self):
        fake = FakeKubectl(
            lab_objects("baseline"),
            web_pods=WEB_PODS,
            probe_output=ok_lines(["web-a", "imposter"]),
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(statuses(out)["AC4"], "FAIL")
        self.assertIn("imposter", out)

    def test_changed_report_image_fails_protected_criterion(self):
        objs = lab_objects("baseline")
        objs[("deployment", "report")] = deployment("report", 1, 1, image="nginx:1")
        fake = FakeKubectl(objs, web_pods=WEB_PODS, probe_output=ok_lines(WEB_PODS))
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertEqual(statuses(out)["AC5"], "FAIL")

    def test_wrong_service_type_fails(self):
        objs = lab_objects("baseline")
        objs[("service", "web")] = service(svc_type="NodePort")
        fake = FakeKubectl(objs, web_pods=WEB_PODS, probe_output=ok_lines(WEB_PODS))
        _, out, _ = run_main("baseline", fake)
        self.assertEqual(statuses(out)["AC2"], "FAIL")


class VariationTests(unittest.TestCase):
    def test_variation_a_modified_deployment_fails_unmodified_criterion(self):
        objs = lab_objects("variation-a")
        objs[("deployment", "web")] = deployment("web", 3, 3, generation=2)
        fake = FakeKubectl(objs, web_pods=WEB_PODS, probe_output=ok_lines(WEB_PODS))
        code, out, _ = run_main("variation-a", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        found = statuses(out)
        self.assertEqual(found["AC5"], "FAIL")
        self.assertEqual(found["AC3"], "PASS")

    def test_variation_a_fix_without_touching_deployment_passes(self):
        fake = FakeKubectl(
            lab_objects("variation-a"),
            web_pods=WEB_PODS,
            probe_output=ok_lines(WEB_PODS),
        )
        code, _, _ = run_main("variation-a", fake)
        self.assertEqual(code, verify.EXIT_PASS)

    def test_variation_b_removing_the_readiness_check_fails(self):
        objs = lab_objects("variation-b")
        objs[("deployment", "web")] = deployment("web", 3, 3, readiness=False)
        fake = FakeKubectl(objs, web_pods=WEB_PODS, probe_output=ok_lines(WEB_PODS))
        code, out, _ = run_main("variation-b", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        self.assertEqual(statuses(out)["AC3"], "FAIL")

    def test_variation_b_publish_not_ready_bypass_fails(self):
        objs = lab_objects("variation-b")
        objs[("service", "web")] = service(publish_not_ready=True)
        fake = FakeKubectl(objs, web_pods=WEB_PODS, probe_output=ok_lines(WEB_PODS))
        _, out, _ = run_main("variation-b", fake)
        self.assertEqual(statuses(out)["AC3"], "FAIL")

    def test_variation_b_initial_state_fails_on_readiness(self):
        objs = lab_objects("variation-b")
        objs[("deployment", "web")] = deployment("web", 3, 0)
        fake = FakeKubectl(
            objs,
            web_pods=WEB_PODS,
            probe_output="ERR\nERR\nERR\nDIAG wget: can't connect: Connection refused",
        )
        code, out, _ = run_main("variation-b", fake)
        self.assertEqual(code, verify.EXIT_FAIL)
        found = statuses(out)
        self.assertEqual(found["AC1"], "FAIL")
        self.assertEqual(found["AC2"], "PASS")


class ErrorHandlingTests(unittest.TestCase):
    def test_kubectl_failure_is_an_error_not_a_fail(self):
        fake = FakeKubectl(
            lab_objects("baseline"),
            web_pods=WEB_PODS,
            probe_output=ok_lines(WEB_PODS),
        )
        fake.error_for[("deployment", "web")] = "Unable to connect to the server"
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_ERROR)
        self.assertEqual(statuses(out)["AC1"], "ERROR")
        self.assertIn("not that your solution is wrong", out)

    def test_probe_failure_is_error_cached_and_cleaned_up(self):
        fake = FakeKubectl(
            lab_objects("baseline"), web_pods=WEB_PODS, exec_error="exec exploded"
        )
        code, out, _ = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_ERROR)
        found = statuses(out)
        self.assertEqual(found["AC3"], "ERROR")
        self.assertEqual(found["AC4"], "ERROR")
        self.assertEqual(fake.verbs().count("exec"), 1, "probe must not be retried")
        self.assertEqual(fake.verbs().count("create"), 1)
        self.assertIn(
            ["delete", "pod", fake.probe_name], [c[:3] for c in fake.calls]
        )

    def test_missing_namespace_is_an_error_before_any_mutation(self):
        fake = FakeKubectl({})
        code, _, err = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_ERROR)
        self.assertIn("scripts/reset.sh baseline", err)
        self.assertNotIn("create", fake.verbs())
        self.assertNotIn("delete", fake.verbs())

    def test_unowned_namespace_is_refused(self):
        objs = {("namespace", "drill-baseline"): namespace("baseline", owned=False)}
        fake = FakeKubectl(objs)
        code, _, err = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_ERROR)
        self.assertIn("not owned by this lab", err)
        self.assertNotIn("create", fake.verbs())

    def test_namespace_for_a_different_scenario_is_an_error(self):
        objs = {("namespace", "drill-baseline"): namespace("variation-a")}
        fake = FakeKubectl(objs)
        code, _, err = run_main("baseline", fake)
        self.assertEqual(code, verify.EXIT_ERROR)
        self.assertIn("belongs to scenario", err)

    def test_error_takes_precedence_over_fail(self):
        criterion = verify.SCENARIOS["baseline"][0]
        results = [
            (criterion, verify.Result(verify.FAIL)),
            (criterion, verify.Result(verify.ERROR)),
        ]
        self.assertEqual(verify.exit_code(results), verify.EXIT_ERROR)

    def test_direct_invocation_without_wrapper_is_rejected(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = verify.main(["baseline"])
        self.assertEqual(code, verify.EXIT_USAGE)
        self.assertIn("scripts/verify.sh", err.getvalue())


class KubectlWrapperTests(unittest.TestCase):
    def test_every_call_pins_kubeconfig_context_and_timeout(self):
        k = verify.Kubectl("/tmp/lab.kubeconfig", "kind-cka-tip-talk")
        with mock.patch.object(verify.subprocess, "run") as run:
            run.return_value = done([])
            k.run(["get", "pods"])
        cmd = run.call_args[0][0]
        self.assertEqual(
            cmd[:5],
            ["kubectl", "--kubeconfig", "/tmp/lab.kubeconfig", "--context", "kind-cka-tip-talk"],
        )
        self.assertTrue(any(a.startswith("--request-timeout=") for a in cmd))
        self.assertIsNotNone(run.call_args[1]["timeout"])

    def test_timeout_becomes_verifier_error(self):
        k = verify.Kubectl("/tmp/lab.kubeconfig", "kind-cka-tip-talk")
        boom = subprocess.TimeoutExpired(cmd="kubectl", timeout=1)
        with mock.patch.object(verify.subprocess, "run", side_effect=boom):
            with self.assertRaises(verify.VerifierError):
                k.run(["get", "pods"], timeout=1)

    def test_missing_kubectl_becomes_verifier_error(self):
        k = verify.Kubectl("/tmp/lab.kubeconfig", "kind-cka-tip-talk")
        with mock.patch.object(verify.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(verify.VerifierError):
                k.run(["get", "pods"])


class ProbeTests(unittest.TestCase):
    def test_probe_manifest_follows_the_lab_rules(self):
        probe = verify.Probe(FakeKubectl({}), "drill-baseline", IMAGE)
        m = probe.manifest()
        c = m["spec"]["containers"][0]
        self.assertRegex(c["image"], r":[0-9]")
        self.assertNotIn("latest", c["image"])
        self.assertIn("requests", c["resources"])
        self.assertIn("limits", c["resources"])
        self.assertTrue(m["spec"]["securityContext"]["runAsNonRoot"])
        self.assertFalse(c["securityContext"]["allowPrivilegeEscalation"])
        self.assertEqual(m["metadata"]["labels"][verify.OWNER_KEY], verify.OWNER_VALUE)
        self.assertIn("activeDeadlineSeconds", m["spec"])

    def test_stale_sweep_only_selects_our_labels(self):
        fake = FakeKubectl(lab_objects("baseline"))
        with verify.Probe(fake, "drill-baseline", IMAGE):
            pass
        sweep = next(c for c in fake.calls if c[0] == "delete" and "-l" in c)
        selector = sweep[sweep.index("-l") + 1]
        self.assertIn(f"{verify.OWNER_KEY}={verify.OWNER_VALUE}", selector)
        self.assertIn(f"{verify.COMPONENT_KEY}={verify.PROBE_COMPONENT}", selector)

    def test_image_pull_failure_is_reported_as_network_problem(self):
        fake = FakeKubectl(lab_objects("baseline"))

        def get_json(args):
            waiting = {"state": {"waiting": {"reason": "ImagePullBackOff"}}}
            return {"status": {"phase": "Pending", "containerStatuses": [waiting]}}

        fake.get_json = get_json
        with self.assertRaises(verify.VerifierError) as ctx:
            with verify.Probe(fake, "drill-baseline", IMAGE):
                pass
        self.assertIn("network", str(ctx.exception))

    def test_parse_and_classify(self):
        sample = verify.parse_probe_output(
            "OK app=web pod=web-a\nERR\nOK app=web pod=web-b\n"
            "DIAG wget: download timed out"
        )
        self.assertEqual(sample.attempted, 3)
        self.assertEqual(sample.failures, 1)
        self.assertEqual(len(sample.responses), 2)
        self.assertEqual(sample.last_error, "connection timed out")
        self.assertEqual(
            verify.classify_error("wget: server returned error: HTTP/1.1 404 Not Found"),
            "the server returned an HTTP error",
        )


class CriteriaTableTests(unittest.TestCase):
    def test_ids_are_sequential_and_unique_per_scenario(self):
        for scenario, criteria in verify.SCENARIOS.items():
            ids = [c.id for c in criteria]
            self.assertEqual(ids, [f"AC{i}" for i in range(1, len(ids) + 1)], scenario)


if __name__ == "__main__":
    unittest.main()

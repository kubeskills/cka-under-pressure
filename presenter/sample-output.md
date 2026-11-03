# Fallback sample output (captured, not invented)

Use this only if the live demo fails. **Say out loud that it is a recording of an earlier run.**

**Provenance:** captured on 2026-11-03 by running the exact commands from
`presenter/runbook.md` against a fresh `scripts/reset.sh baseline` on one machine
(macOS, Docker Desktop 29.6.1, kind v0.30.0, kubectl client v1.34.2, Kubernetes server
v1.34.0, single node). Pod name suffixes, IPs and ages differ on every run. Output was
captured by script; only this header and the section titles were added.

### Part 3 — Orient

```text
$ kubectl config current-context
kind-cka-tip-talk
[exit code: 0]
```

### Part 3 — Orient (what exists)

```text
$ kubectl -n drill-baseline get deployment,pods
NAME                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/report   1/1     1            1           2s
deployment.apps/web      1/1     1            1           2s

NAME                          READY   STATUS    RESTARTS   AGE
pod/report-6965757fbc-9zpls   1/1     Running   0          2s
pod/web-655fd4d859-gcsdg      1/1     Running   0          2s
[exit code: 0]
```

### Part 4 — Solve, with the controlled mistake

```text
$ kubectl -n drill-baseline scale deployment web --replicas=3
deployment.apps/web scaled
[exit code: 0]
```

### Part 4 — (continued)

```text
$ kubectl -n drill-baseline expose deployment web --port=80
service/web exposed
[exit code: 0]
```

### Part 5 — Verify: the task is NOT done

```text
$ scripts/verify.sh baseline
CKA Under Pressure lab check (not official CKA scoring)
Scenario: baseline   Context: kind-cka-tip-talk   Namespace: drill-baseline

  PASS  AC1  Deployment `web` has 3 replicas, all Ready
  PASS  AC2  A Service named `web` exists, type ClusterIP, port 80
  FAIL  AC3  Requests to the Service on port 80 from inside the namespace succeed
        -> 0/3 requests to http://web.drill-baseline.svc:80/ succeeded; connection refused
  FAIL  AC4  Only `web` Pods answer, and more than one of them does
        -> not evaluated: no successful responses
  PASS  AC5  Protected resources are intact (`report`, the `web` image, NetworkPolicy)

Result: 3 passed, 2 failed, 0 error(s)
[exit code: 1]
```

### Part 6 — Fix: read the port, change one field

```text
$ kubectl -n drill-baseline get deployment web -o jsonpath='{.spec.template.spec.containers[0].ports}{"\n"}'
[{"containerPort":8080,"name":"http","protocol":"TCP"}]
[exit code: 0]
```

### Part 6 — (continued)

```text
$ kubectl -n drill-baseline patch service web --type merge -p '{"spec":{"ports":[{"port":80,"targetPort":8080}]}}'
service/web patched
[exit code: 0]
```

### Part 6 — Verify again

```text
$ scripts/verify.sh baseline
CKA Under Pressure lab check (not official CKA scoring)
Scenario: baseline   Context: kind-cka-tip-talk   Namespace: drill-baseline

  PASS  AC1  Deployment `web` has 3 replicas, all Ready
  PASS  AC2  A Service named `web` exists, type ClusterIP, port 80
  PASS  AC3  Requests to the Service on port 80 from inside the namespace succeed
  PASS  AC4  Only `web` Pods answer, and more than one of them does
  PASS  AC5  Protected resources are intact (`report`, the `web` image, NetworkPolicy)

Result: 5 passed, 0 failed, 0 error(s)
[exit code: 0]
```

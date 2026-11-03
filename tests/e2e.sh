#!/usr/bin/env bash
# End-to-end lab test against the EXISTING lab cluster. It never creates or deletes
# the cluster. It does reset, delete and recreate the drill-* namespaces in it, so it
# requires --yes.
#
#   tests/e2e.sh --yes [--log FILE]
#
# For every scenario it checks: initial state fails verification; the documented
# reference solution passes; repeated verification still passes and leaves no probe
# Pod; reset restores the identical initial failure; setup output does not leak
# answers. It also checks the presenter's controlled mistake and recovery, that a
# wrong context is refused before any mutation, and namespace ownership guards.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../scripts/lib/common.sh
source "$ROOT/scripts/lib/common.sh"

yes=0
log=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) yes=1 ;;
    --log)
      log="${2:-}"
      shift
      ;;
    *)
      echo "Usage: tests/e2e.sh --yes [--log FILE]" >&2
      exit "$EX_USAGE"
      ;;
  esac
  shift
done
if [[ "$yes" -ne 1 ]]; then
  echo "This test resets and deletes the drill-* namespaces in the '$LAB_CLUSTER_NAME' cluster." >&2
  echo "Re-run with --yes to proceed." >&2
  exit "$EX_DECLINED"
fi
if [[ -n "$log" ]]; then
  exec > >(tee "$log") 2>&1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0
fail=0

ok() {
  echo "PASS  $*"
  pass=$((pass + 1))
}
bad() {
  echo "FAIL  $*"
  fail=$((fail + 1))
}

# t_run WANT_EXIT DESCRIPTION COMMAND...   (output kept in $TMP/out, exit in LAST_RC)
t_run() {
  local want="$1" desc="$2"
  shift 2
  "$@" >"$TMP/out" 2>&1 </dev/null
  LAST_RC=$?
  if [[ "$LAST_RC" -eq "$want" ]]; then
    ok "$desc (exit $LAST_RC)"
  else
    bad "$desc (exit $LAST_RC, wanted $want)"
    sed 's/^/      | /' "$TMP/out"
  fi
}

# Parses verify output into "AC1:PASS AC2:FAIL ..." for exact comparison.
statuses() {
  awk '$1 ~ /^(PASS|FAIL|ERROR)$/ && $2 ~ /^AC[0-9]+$/ { printf "%s%s:%s", sep, $2, $1; sep = " " }' "$1"
}

expect_statuses() { # description expected
  local got
  got="$(statuses "$TMP/out")"
  if [[ "$got" == "$2" ]]; then
    ok "$1: $got"
  else
    bad "$1: got '$got', wanted '$2'"
  fi
}

# Runs the single fenced block with the given info string from a Markdown file.
run_block() { # file tag
  awk -v tag="$2" '
    $0 == "```bash " tag { on = 1; next }
    on && $0 == "```" { on = 0; next }
    on { print }' "$1" >"$TMP/block.sh"
  [[ -s "$TMP/block.sh" ]] || return 99
  KUBECONFIG="$LAB_KUBECONFIG" bash -eu -o pipefail "$TMP/block.sh"
}

ns_uid() { lab_kubectl get namespace "$1" -o jsonpath='{.metadata.uid}' 2>/dev/null; }

initial_state() { # scenario -> expected "AC:STATUS" string for a fresh seed
  case "$1" in
    baseline) echo "AC1:FAIL AC2:FAIL AC3:FAIL AC4:FAIL AC5:PASS" ;;
    variation-a) echo "AC1:PASS AC2:PASS AC3:FAIL AC4:FAIL AC5:PASS AC6:PASS" ;;
    variation-b) echo "AC1:FAIL AC2:PASS AC3:PASS AC4:FAIL AC5:FAIL AC6:PASS" ;;
  esac
}
solved_state() {
  case "$1" in
    baseline) echo "AC1:PASS AC2:PASS AC3:PASS AC4:PASS AC5:PASS" ;;
    *) echo "AC1:PASS AC2:PASS AC3:PASS AC4:PASS AC5:PASS AC6:PASS" ;;
  esac
}

echo "== Environment"
echo "date:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "kubectl: $(kubectl version --client -o yaml 2>/dev/null | awk '/gitVersion:/ {print $2; exit}')"
echo "kind:    $(kind version 2>/dev/null | head -n 1)"
echo "python:  $(python3 --version 2>&1)"
echo "bash:    ${BASH_VERSION}"
echo "docker:  $(docker version --format 'client {{.Client.Version}} / server {{.Server.Version}}' 2>/dev/null)"
(lab_guard) || {
  echo "Lab cluster guard failed; is the cluster up? (scripts/cluster-up.sh)" >&2
  exit "$EX_ENV"
}
echo "server:  $(lab_kubectl version -o yaml 2>/dev/null | awk '/serverVersion:/ {f=1} f && /gitVersion:/ {print $2; exit}')"
echo "node:    $(lab_kubectl get nodes -o jsonpath='{.items[0].status.nodeInfo.kubeletVersion} / {.items[0].status.nodeInfo.containerRuntimeVersion}' 2>/dev/null)"

for s in $LAB_SCENARIOS; do
  ns="$(scenario_ns "$s")"
  echo
  echo "== Scenario: $s ($ns)"

  t_run 0 "$s: reset seeds the starting state" "$ROOT/scripts/reset.sh" --yes "$s"
  # Setup output must not enumerate resources or hint at the cause.
  if grep -Eqi 'targetPort|selector|probe|readiness|/healthz|/ready|service/|fault|solution|app: web' "$TMP/out"; then
    bad "$s: setup output leaks solution vocabulary"
    sed 's/^/      | /' "$TMP/out"
  else
    ok "$s: setup output does not leak answers"
  fi
  uid_before="$(ns_uid "$ns")"

  t_run 1 "$s: initial state FAILS verification" "$ROOT/scripts/verify.sh" "$s"
  expect_statuses "$s: initial criteria" "$(initial_state "$s")"
  initial_out="$(statuses "$TMP/out")"

  if run_block "$ROOT/solutions/$s.md" solution >"$TMP/sol.out" 2>&1; then
    ok "$s: documented reference solution ran"
  else
    bad "$s: documented reference solution failed"
    sed 's/^/      | /' "$TMP/sol.out"
  fi

  t_run 0 "$s: reference solution PASSES verification" "$ROOT/scripts/verify.sh" "$s"
  expect_statuses "$s: solved criteria" "$(solved_state "$s")"
  t_run 0 "$s: repeated verification still PASSES" "$ROOT/scripts/verify.sh" "$s"
  t_run 0 "$s: verification once more (idempotent)" "$ROOT/scripts/verify.sh" "$s"

  leftovers="$(lab_kubectl -n "$ns" get pods -l app.kubernetes.io/component=verifier-probe -o name 2>/dev/null)"
  if [[ -z "$leftovers" ]]; then
    ok "$s: no verifier probe Pods accumulate"
  else
    bad "$s: leftover probe Pods: $leftovers"
  fi

  t_run 0 "$s: reset after solving" "$ROOT/scripts/reset.sh" --yes "$s"
  uid_after="$(ns_uid "$ns")"
  if [[ -n "$uid_before" && "$uid_before" != "$uid_after" ]]; then
    ok "$s: reset recreated the namespace (new UID)"
  else
    bad "$s: reset did not recreate the namespace"
  fi
  t_run 1 "$s: reset restores the failing initial state" "$ROOT/scripts/verify.sh" "$s"
  expect_statuses "$s: criteria after reset match initial" "$initial_out"
done

echo
echo "== Presenter demo: controlled mistake and recovery (baseline)"
t_run 0 "reset baseline" "$ROOT/scripts/reset.sh" --yes baseline
if run_block "$ROOT/presenter/runbook.md" demo-mistake >"$TMP/mistake.out" 2>&1; then
  ok "demo-mistake commands succeed (the mistake looks like success)"
  sed 's/^/      | /' "$TMP/mistake.out"
else
  bad "demo-mistake commands failed"
  sed 's/^/      | /' "$TMP/mistake.out"
fi
t_run 1 "after the mistake, verification FAILS" "$ROOT/scripts/verify.sh" baseline
expect_statuses "mistake criteria" "AC1:PASS AC2:PASS AC3:FAIL AC4:FAIL AC5:PASS"
grep -E 'AC3' -A1 "$TMP/out" | sed 's/^/      | /'
if run_block "$ROOT/presenter/runbook.md" demo-recover >"$TMP/recover.out" 2>&1; then
  ok "demo-recover commands succeed"
else
  bad "demo-recover commands failed"
  sed 's/^/      | /' "$TMP/recover.out"
fi
t_run 0 "after recovery, verification PASSES" "$ROOT/scripts/verify.sh" baseline
t_run 0 "reset baseline after demo" "$ROOT/scripts/reset.sh" --yes baseline

echo
echo "== Wrong context is refused before any mutation"
uid_baseline="$(ns_uid drill-baseline)"
cp "$LAB_KUBECONFIG" "$TMP/wrong.kubeconfig"
kubectl --kubeconfig "$TMP/wrong.kubeconfig" config rename-context "$LAB_CONTEXT" kind-not-the-lab >/dev/null 2>&1
for cmd in "reset.sh --yes baseline" "reset.sh --yes --all" "clean.sh --yes" "verify.sh baseline"; do
  # shellcheck disable=SC2086
  t_run 3 "wrong context: scripts/$cmd" env LAB_KUBECONFIG="$TMP/wrong.kubeconfig" "$ROOT/scripts/${cmd%% *}" ${cmd#* }
done
if [[ "$(ns_uid drill-baseline)" == "$uid_baseline" ]]; then
  ok "drill-baseline untouched by refused commands (same UID)"
else
  bad "drill-baseline was modified by a refused command"
fi
t_run 1 "default \$KUBECONFIG is ignored (nonexistent path set)" env KUBECONFIG=/nonexistent "$ROOT/scripts/verify.sh" baseline

echo
echo "== Namespace ownership guard"
t_run 0 "clean variation-a" "$ROOT/scripts/clean.sh" --yes variation-a
lab_kubectl create namespace drill-variation-a >/dev/null 2>&1
t_run 3 "reset refuses an unlabelled namespace with a lab name" "$ROOT/scripts/reset.sh" --yes variation-a
t_run 0 "clean skips an unlabelled namespace" "$ROOT/scripts/clean.sh" --yes variation-a
if lab_kubectl get namespace drill-variation-a >/dev/null 2>&1; then
  ok "unlabelled namespace was left alone"
else
  bad "unlabelled namespace was deleted"
fi
# Remove only the fixture this test created, then restore the scenario.
lab_kubectl delete namespace drill-variation-a --wait=true --timeout=120s >/dev/null 2>&1
t_run 0 "restore variation-a" "$ROOT/scripts/reset.sh" --yes variation-a

echo
echo "== Final state: all scenarios freshly seeded"
t_run 0 "reset --all" "$ROOT/scripts/reset.sh" --yes --all

echo
echo "e2e: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]

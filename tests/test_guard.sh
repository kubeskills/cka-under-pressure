#!/usr/bin/env bash
# Proves the context guard refuses unsafe targets BEFORE any mutating kubectl call.
# Uses a fake `kubectl` on PATH that records every invocation; no cluster needed.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/bin"
cat >"$TMP/bin/kubectl" <<'SHIM'
#!/usr/bin/env bash
echo "$*" >>"$SHIM_LOG"
case "$*" in
  *"config get-contexts -o name"*) printf '%s\n' "${SHIM_CONTEXTS:-kind-other}" ;;
  *"config view --minify"*) printf '%s' "${SHIM_SERVER:-https://127.0.0.1:1234}" ;;
  *"get nodes -o name"*) printf '%s\n' "${SHIM_NODES:-node/other}" ;;
  # Real kubectl rejects a selector combined with a resource name; mimic that so the
  # ownership helper cannot regress to that form without this suite noticing.
  *"get namespace "*" -l "*)
    echo "error: name cannot be provided when a selector is specified" >&2
    exit 1
    ;;
  *"get namespaces -l "*) printf '%s\n' "${SHIM_OWNED:-}" ;;
  *)
    echo "shim: unexpected call: $*" >&2
    exit 1
    ;;
esac
SHIM
chmod +x "$TMP/bin/kubectl"
: >"$TMP/fake.kubeconfig"

MUTATING='(^| )(apply|create|delete|patch|replace|run|exec|scale|label|annotate|set|expose|edit|rollout|drain|cordon|taint)( |$)'
pass=0
fail=0

# expect_exit DESCRIPTION EXPECTED_CODE -- ENV=VAL... COMMAND...
expect_exit() {
  local desc="$1" want="$2" got
  shift 3
  : >"$TMP/log"
  env PATH="$TMP/bin:$PATH" SHIM_LOG="$TMP/log" LAB_KUBECONFIG="$TMP/fake.kubeconfig" "$@" \
    </dev/null >"$TMP/out" 2>&1
  got=$?
  if [[ "$got" -ne "$want" ]]; then
    echo "FAIL: $desc (exit $got, wanted $want)"
    sed 's/^/        /' "$TMP/out"
    fail=$((fail + 1))
    return
  fi
  if grep -Eq "$MUTATING" "$TMP/log"; then
    echo "FAIL: $desc (a mutating kubectl call was made)"
    sed 's/^/        /' "$TMP/log"
    fail=$((fail + 1))
    return
  fi
  echo "ok:   $desc"
  pass=$((pass + 1))
}

scripts=(
  "reset.sh --yes baseline"
  "reset.sh --yes --all"
  "clean.sh --yes"
  "verify.sh baseline"
)

for s in "${scripts[@]}"; do
  # shellcheck disable=SC2086  # intentional word splitting of "script args"
  set -- $s
  name="$1"
  shift
  expect_exit "$name: kubeconfig without the lab context is refused (exit 3)" 3 -- \
    SHIM_CONTEXTS="kind-other" "$ROOT/scripts/$name" "$@"
  expect_exit "$name: lab-named context pointing at a remote API is refused (exit 3)" 3 -- \
    SHIM_CONTEXTS="kind-cka-tip-talk" SHIM_SERVER="https://prod.example.com:6443" "$ROOT/scripts/$name" "$@"
  expect_exit "$name: local API but not the lab node is refused (exit 3)" 3 -- \
    SHIM_CONTEXTS="kind-cka-tip-talk" SHIM_NODES="node/other-control-plane" "$ROOT/scripts/$name" "$@"
  expect_exit "$name: missing kubeconfig is an environment error (exit 4)" 4 -- \
    LAB_KUBECONFIG="$TMP/does-not-exist" "$ROOT/scripts/$name" "$@"
done

expect_exit "reset.sh: unknown scenario is a usage error and never calls kubectl (exit 2)" 2 -- \
  "$ROOT/scripts/reset.sh" --yes nonsense
if [[ -s "$TMP/log" ]]; then
  echo "FAIL: reset.sh made kubectl calls for an unknown scenario"
  fail=$((fail + 1))
fi
expect_exit "verify.sh: missing scenario is a usage error (exit 2)" 2 -- "$ROOT/scripts/verify.sh"

# Positive control: with a matching lab, the guard must pass, ignore $KUBECONFIG,
# and pin --kubeconfig on every call.
expect_exit "guard passes for a matching lab (positive control)" 0 -- \
  SHIM_CONTEXTS="kind-cka-tip-talk" SHIM_NODES="node/cka-tip-talk-control-plane" \
  KUBECONFIG="/nonexistent/ignored" \
  bash -c "source '$ROOT/scripts/lib/common.sh'; lab_guard"
if grep -Fv -- "--kubeconfig $TMP/fake.kubeconfig" "$TMP/log" | grep -q .; then
  echo "FAIL: a kubectl call did not pin --kubeconfig"
  sed 's/^/        /' "$TMP/log"
  fail=$((fail + 1))
else
  echo "ok:   every kubectl call pins --kubeconfig (user's default kubeconfig is not consulted)"
  pass=$((pass + 1))
fi

# Ownership helper: only namespaces in the labelled list count, matched by exact name.
OWN="source '$ROOT/scripts/lib/common.sh'; ns_is_lab_owned"
expect_exit "ownership: labelled namespace is recognised" 0 -- \
  SHIM_OWNED="$(printf 'namespace/drill-baseline\nnamespace/drill-variation-a')" \
  bash -c "$OWN drill-baseline"
expect_exit "ownership: namespace missing from the labelled list is rejected" 1 -- \
  SHIM_OWNED="namespace/drill-baseline" bash -c "$OWN drill-variation-a"
expect_exit "ownership: similarly named namespace is not confused (exact match)" 1 -- \
  SHIM_OWNED="namespace/drill-baseline-extra" bash -c "$OWN drill-baseline"
expect_exit "ownership: empty labelled list rejects everything" 1 -- \
  SHIM_OWNED="" bash -c "$OWN drill-baseline"

echo
echo "guard tests: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]

#!/usr/bin/env bash
# Run the lab acceptance checks for one scenario. Lab checks only; this is not
# official CKA scoring. Exit codes: 0 all PASS, 1 a criterion FAILed, 2 usage,
# 3 refused (wrong context/cluster), 4 ERROR (environment or verifier problem).
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/verify.sh [--diagnose] [--grace SECONDS] <baseline|variation-a|variation-b>

Checks the scenario's published acceptance criteria (see tasks/<scenario>.md).
  --diagnose       also print read-only cluster observations (no advice)
  --grace SECONDS  how long to wait for Pods to become Ready (default 10)

It creates one short-lived, labelled probe Pod in the scenario namespace to test
the Service from inside the cluster, and deletes it before exiting.
EOF
}

scenario=""
py_args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --diagnose) py_args+=("--diagnose") ;;
    --grace)
      [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || {
        err "--grace needs a whole number of seconds"
        exit "$EX_USAGE"
      }
      py_args+=("--grace" "$2")
      shift
      ;;
    -*)
      usage >&2
      exit "$EX_USAGE"
      ;;
    *)
      [[ -z "$scenario" ]] || {
        usage >&2
        exit "$EX_USAGE"
      }
      scenario="$1"
      ;;
  esac
  shift
done
[[ -n "$scenario" ]] || {
  usage >&2
  exit "$EX_USAGE"
}
valid_scenario "$scenario" || {
  err "Unknown scenario '$scenario' (expected one of: $LAB_SCENARIOS)"
  exit "$EX_USAGE"
}

require_cmd python3 "Needed by the verifier."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' ||
  die "$EX_ENV" "python3 >= 3.8 is required."

lab_guard

# The guard above is the single place that validates the context; verify.py
# trusts these values and passes them to every kubectl call it makes.
# ${py_args[@]+...} keeps bash 3.2 happy when the array is empty under `set -u`.
exec env LAB_KUBECONFIG="$LAB_KUBECONFIG" LAB_CONTEXT="$LAB_CONTEXT" \
  LAB_NAMESPACE="$(scenario_ns "$scenario")" \
  python3 "$LAB_ROOT/scripts/lib/verify.py" "$scenario" ${py_args[@]+"${py_args[@]}"}

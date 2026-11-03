#!/usr/bin/env bash
# Create or reset lab namespaces to their seeded starting state (namespace-level only).
# Deletes and recreates 'drill-<scenario>'; it never touches the cluster itself
# or any namespace that lacks the lab ownership label.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/reset.sh [--yes] <baseline|variation-a|variation-b>...
       scripts/reset.sh [--yes] --all

Creates the scenario's namespace in its starting state. If the namespace already
exists, asks before deleting it and everything in it (including your work), then
recreates it. Safe to repeat: every reset produces the same starting state.
EOF
}

scenarios=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y | --yes) LAB_ASSUME_YES=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    --all) read -r -a scenarios <<<"$LAB_SCENARIOS" ;;
    -*)
      usage >&2
      exit "$EX_USAGE"
      ;;
    *)
      valid_scenario "$1" || {
        err "Unknown scenario '$1' (expected one of: $LAB_SCENARIOS)"
        exit "$EX_USAGE"
      }
      scenarios+=("$1")
      ;;
  esac
  shift
done
if [[ ${#scenarios[@]} -eq 0 ]]; then
  usage >&2
  exit "$EX_USAGE"
fi

# variation-b intentionally starts with Pods that never become Ready, so "seeded"
# means "Pods are Running" there and "Pods are Available" everywhere else.
seed_ready() {
  local ns="$1" scenario="$2" want running avail
  want="$(lab_kubectl -n "$ns" get deployment web -o jsonpath='{.spec.replicas}' 2>/dev/null)" || return 1
  [[ -n "$want" ]] || return 1
  running="$(lab_kubectl -n "$ns" get pods -l app.kubernetes.io/name=web \
    -o jsonpath='{range .items[*]}{.status.phase}{"\n"}{end}' 2>/dev/null | grep -c '^Running$' || true)"
  [[ "$running" == "$want" ]] || return 1
  if [[ "$scenario" != "variation-b" ]]; then
    avail="$(lab_kubectl -n "$ns" get deployment web -o jsonpath='{.status.availableReplicas}' 2>/dev/null)" || return 1
    [[ "$avail" == "$want" ]] || return 1
  fi
  avail="$(lab_kubectl -n "$ns" get deployment report -o jsonpath='{.status.availableReplicas}' 2>/dev/null)" || return 1
  [[ "$avail" == "1" ]]
}

reset_one() {
  local scenario="$1" ns
  ns="$(scenario_ns "$scenario")"

  if ns_exists "$ns"; then
    ns_is_lab_owned "$ns" ||
      die "$EX_REFUSED" "Namespace '$ns' exists but lacks the label ${LAB_OWNER_SELECTOR}. Refusing to delete a namespace this lab does not own."
    confirm "Delete namespace '$ns' and everything in it, then recreate the '$scenario' starting state?" ||
      die "$EX_DECLINED" "Aborted; nothing was changed."
    info "Deleting namespace $ns ..."
    lab_kubectl delete namespace "$ns" --wait=true --timeout=180s >/dev/null
  fi

  info "Seeding '$scenario' into namespace $ns ..."
  # Output is discarded so setup does not enumerate what exists (some scenarios
  # start with a seeded fault).
  lab_kubectl apply -k "$LAB_ROOT/lab/scenarios/$scenario" >/dev/null
  wait_until 180 "scenario '$scenario' to reach its starting state" seed_ready "$ns" "$scenario" ||
    die "$EX_ENV" "Seeding did not finish. The first run downloads the app image; check network access, then retry."
  info "Ready: scenario '$scenario' in namespace $ns. Brief: tasks/$scenario.md"
}

lab_guard
for s in "${scenarios[@]}"; do
  reset_one "$s"
done

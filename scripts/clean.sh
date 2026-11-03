#!/usr/bin/env bash
# Remove lab namespaces but keep the cluster (namespace-level cleanup only).
# Only namespaces carrying the lab ownership label are ever deleted.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/clean.sh [--yes] [<baseline|variation-a|variation-b>...]

Deletes the named lab namespaces (default: all three) after confirmation.
The kind cluster is kept; use scripts/cluster-down.sh to remove it.
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
  read -r -a scenarios <<<"$LAB_SCENARIOS"
fi

lab_guard

targets=()
for s in "${scenarios[@]}"; do
  ns="$(scenario_ns "$s")"
  if ! ns_exists "$ns"; then
    info "Namespace $ns does not exist; skipping."
  elif ! ns_is_lab_owned "$ns"; then
    warn "Namespace $ns lacks the label ${LAB_OWNER_SELECTOR}; skipping it."
  else
    targets+=("$ns")
  fi
done

if [[ ${#targets[@]} -eq 0 ]]; then
  info "Nothing to clean."
  exit 0
fi

confirm "Delete namespace(s) ${targets[*]} and everything in them?" ||
  die "$EX_DECLINED" "Aborted; nothing was deleted."
for ns in "${targets[@]}"; do
  info "Deleting namespace $ns ..."
  lab_kubectl delete namespace "$ns" --wait=true --timeout=180s >/dev/null
done
info "Done. The cluster is still running (scripts/cluster-down.sh removes it)."

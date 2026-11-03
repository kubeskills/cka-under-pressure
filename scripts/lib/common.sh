#!/usr/bin/env bash
# Shared helpers for the CKA Under Pressure lab scripts. Source; do not execute.
# shellcheck disable=SC2034  # library: constants are consumed by the sourcing scripts
# Targets bash 3.2 (macOS default): no associative arrays, mapfile, or ${var,,}.
#
# Safety model:
#   * Every kubectl call goes through lab_kubectl, which passes --kubeconfig and
#     --context explicitly. The user's default kubeconfig and current-context are
#     never read or modified.
#   * lab_guard must pass before any script changes anything. It refuses unless the
#     context, the API server address, and the node name all look like the lab.

if [ -z "${BASH_VERSION:-}" ]; then
  echo "ERROR: scripts/lib/common.sh must be sourced from bash (zsh and sh do not set BASH_SOURCE)." >&2
  return 1
fi
if [[ -n "${LAB_COMMON_LOADED:-}" ]]; then
  return 0
fi
LAB_COMMON_LOADED=1

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly LAB_ROOT

readonly LAB_CLUSTER_NAME="cka-tip-talk"
readonly LAB_CONTEXT="kind-${LAB_CLUSTER_NAME}"
readonly LAB_NODE_NAME="${LAB_CLUSTER_NAME}-control-plane"
readonly LAB_OWNER_KEY="app.kubernetes.io/managed-by"
readonly LAB_OWNER_VALUE="cka-under-pressure"
readonly LAB_OWNER_SELECTOR="${LAB_OWNER_KEY}=${LAB_OWNER_VALUE}"
readonly LAB_SCENARIOS="baseline variation-a variation-b"

# LAB_KUBECONFIG may be overridden (the tests do); the context may not.
LAB_KUBECONFIG="${LAB_KUBECONFIG:-${LAB_ROOT}/.kube/${LAB_CLUSTER_NAME}.kubeconfig}"
export LAB_KUBECONFIG

# Exit codes shared by all scripts (documented in README.md). They are consumed by the
# scripts that source this file (see the file-level SC2034 note at the top).
readonly EX_FAIL=1     # verify: an acceptance criterion is not met
readonly EX_USAGE=2    # bad arguments
readonly EX_REFUSED=3  # unexpected context/cluster; nothing was changed
readonly EX_ENV=4      # prerequisite, connectivity, or verifier problem
readonly EX_DECLINED=5 # confirmation declined or unavailable; nothing changed

info() { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
err() { printf 'ERROR: %s\n' "$*" >&2; }
die() {
  local code="$1"
  shift
  err "$*"
  exit "$code"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "$EX_ENV" "Required command not found: $1. ${2:-}"
}

lab_kubectl() {
  kubectl --kubeconfig "$LAB_KUBECONFIG" --context "$LAB_CONTEXT" "$@"
}

valid_scenario() {
  local s
  for s in $LAB_SCENARIOS; do
    [[ "$s" == "$1" ]] && return 0
  done
  return 1
}

scenario_ns() {
  valid_scenario "$1" || return 1
  printf 'drill-%s\n' "$1"
}

# Prints the first value of an `image:` key in a manifest. Keeps image pins in
# one place (the manifests) instead of repeating them in scripts.
manifest_image() {
  awk '$1 == "image:" { print $2; exit }' "$1"
}

confirm() {
  if [[ "${LAB_ASSUME_YES:-0}" == "1" ]]; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    err "Confirmation required but stdin is not a terminal. Re-run with --yes to proceed."
    return 1
  fi
  local reply
  read -r -p "$1 [y/N] " reply
  [[ "$reply" == "y" || "$reply" == "Y" || "$reply" == "yes" ]]
}

# Refuses (exit 3) or fails (exit 4) unless we are talking to the lab cluster.
lab_guard() {
  require_cmd kubectl "Install kubectl, then re-run."
  [[ -f "$LAB_KUBECONFIG" ]] ||
    die "$EX_ENV" "Lab kubeconfig not found: $LAB_KUBECONFIG. Create the lab with scripts/cluster-up.sh."

  local contexts server nodes
  contexts="$(kubectl --kubeconfig "$LAB_KUBECONFIG" config get-contexts -o name 2>/dev/null)" ||
    die "$EX_ENV" "Cannot read kubeconfig: $LAB_KUBECONFIG"
  printf '%s\n' "$contexts" | grep -Fxq -- "$LAB_CONTEXT" ||
    die "$EX_REFUSED" "Refusing to continue: $LAB_KUBECONFIG has no context named '$LAB_CONTEXT'. Nothing was changed."

  server="$(kubectl --kubeconfig "$LAB_KUBECONFIG" --context "$LAB_CONTEXT" \
    config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null)" ||
    die "$EX_ENV" "Cannot read the API server address for context '$LAB_CONTEXT'."
  case "$server" in
    https://127.0.0.1:* | https://localhost:* | 'https://[::1]:'*) ;;
    *) die "$EX_REFUSED" "Refusing to continue: context '$LAB_CONTEXT' points at '$server', not a local kind API server. Nothing was changed." ;;
  esac

  nodes="$(lab_kubectl --request-timeout=10s get nodes -o name 2>/dev/null)" ||
    die "$EX_ENV" "Cannot reach the lab cluster API at $server. Is Docker running? Try scripts/preflight.sh."
  printf '%s\n' "$nodes" | grep -Fxq -- "node/${LAB_NODE_NAME}" ||
    die "$EX_REFUSED" "Refusing to continue: node '${LAB_NODE_NAME}' not found, so this is not the lab cluster. Nothing was changed."
}

# 0 = exists, 1 = does not exist; any other API error aborts rather than guessing.
ns_exists() {
  local out
  if out="$(lab_kubectl --request-timeout=15s get namespace "$1" -o name 2>&1)"; then
    return 0
  fi
  case "$out" in
    *NotFound* | *"not found"*) return 1 ;;
    *) die "$EX_ENV" "Could not query namespace '$1': $out" ;;
  esac
}

# True only if the namespace carries the lab ownership label.
# kubectl rejects a label selector combined with a resource name, so list the owned
# namespaces and look for this one. The output is captured first (not piped into
# `grep -q`) so pipefail cannot turn an early grep exit into a false negative.
ns_is_lab_owned() {
  local owned
  owned="$(lab_kubectl --request-timeout=15s get namespaces -l "$LAB_OWNER_SELECTOR" -o name 2>/dev/null)" || return 1
  [[ $'\n'"$owned"$'\n' == *$'\n'"namespace/$1"$'\n'* ]]
}

# wait_until TIMEOUT_SECONDS DESCRIPTION COMMAND [ARGS...]
wait_until() {
  local timeout="$1" desc="$2" waited=0
  shift 2
  until "$@"; do
    if ((waited >= timeout)); then
      err "Timed out after ${timeout}s waiting for: ${desc}"
      return 1
    fi
    sleep 2
    waited=$((waited + 2))
  done
}

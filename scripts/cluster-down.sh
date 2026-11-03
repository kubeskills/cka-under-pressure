#!/usr/bin/env bash
# Delete the dedicated kind cluster (cluster lifecycle only). Confirmation-gated.
# Only the cluster named exactly 'cka-tip-talk' is targeted.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/cluster-down.sh [--yes]

Deletes the kind cluster 'cka-tip-talk' and the repo-local .kube/ kubeconfig.
All lab namespaces and any work in them are lost. Other clusters are untouched.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y | --yes) LAB_ASSUME_YES=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit "$EX_USAGE"
      ;;
  esac
  shift
done

require_cmd kind "See https://kind.sigs.k8s.io/docs/user/quick-start/#installation"

if ! kind get clusters 2>/dev/null | grep -Fxq "$LAB_CLUSTER_NAME"; then
  info "No kind cluster named '$LAB_CLUSTER_NAME' exists. Nothing to do."
  exit 0
fi

cat <<EOF
This will DELETE the kind cluster '$LAB_CLUSTER_NAME' and everything in it.
Other kind clusters and your ~/.kube/config are not touched.
EOF
confirm "Delete the cluster?" || die "$EX_DECLINED" "Aborted; nothing was deleted."

# Delete against the dedicated kubeconfig so the user's default file is never edited.
if [[ ! -f "$LAB_KUBECONFIG" ]]; then
  umask 077
  mkdir -p "$(dirname "$LAB_KUBECONFIG")"
  kind export kubeconfig --name "$LAB_CLUSTER_NAME" --kubeconfig "$LAB_KUBECONFIG"
fi
kind delete cluster --name "$LAB_CLUSTER_NAME" --kubeconfig "$LAB_KUBECONFIG"

# Remove the kubeconfig only if it is the repo-local default, never a user override.
if [[ "$LAB_KUBECONFIG" == "$LAB_ROOT/.kube/${LAB_CLUSTER_NAME}.kubeconfig" ]]; then
  rm -f "$LAB_KUBECONFIG"
fi
info "Cluster '$LAB_CLUSTER_NAME' deleted."

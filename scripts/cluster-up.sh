#!/usr/bin/env bash
# Create the dedicated kind cluster for this lab (cluster lifecycle only).
# Writes credentials to .kube/cka-tip-talk.kubeconfig inside this repo, so
# ~/.kube/config and your current kubectl context are left alone.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/cluster-up.sh [--yes]

Creates the single-node kind cluster 'cka-tip-talk' (asks first unless --yes).
If it already exists, only refreshes the dedicated kubeconfig.
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

require_cmd docker "Install Docker (or another container runtime supported by kind)."
require_cmd kind "See https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
require_cmd kubectl "See https://kubernetes.io/docs/tasks/tools/"
docker info >/dev/null 2>&1 || die "$EX_ENV" "The Docker daemon is not reachable. Start Docker and retry."

umask 077
mkdir -p "$(dirname "$LAB_KUBECONFIG")"

if kind get clusters 2>/dev/null | grep -Fxq "$LAB_CLUSTER_NAME"; then
  info "Cluster '$LAB_CLUSTER_NAME' already exists. Refreshing $LAB_KUBECONFIG only."
  kind export kubeconfig --name "$LAB_CLUSTER_NAME" --kubeconfig "$LAB_KUBECONFIG"
else
  node_image="$(manifest_image "$LAB_ROOT/lab/kind-cluster.yaml")"
  cat <<EOF
This will create ONE new kind cluster:
  name        : $LAB_CLUSTER_NAME  (a single Docker container; other kind clusters are untouched)
  node image  : ${node_image%%@*}  (kind downloads it from the network if it is not cached)
  kubeconfig  : $LAB_KUBECONFIG  (your ~/.kube/config is not modified)
EOF
  confirm "Create the cluster?" || die "$EX_DECLINED" "Aborted; nothing was created."
  kind create cluster --name "$LAB_CLUSTER_NAME" \
    --config "$LAB_ROOT/lab/kind-cluster.yaml" \
    --kubeconfig "$LAB_KUBECONFIG" --wait 180s
fi

lab_guard
cat <<EOF

Cluster is ready. In each terminal where you practice, point kubectl at it:

  export KUBECONFIG="$LAB_KUBECONFIG"

Then seed a scenario:  scripts/reset.sh baseline
EOF

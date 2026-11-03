#!/usr/bin/env bash
# Read-only environment check. Changes nothing and pulls nothing.
# Exit 0 = required tools present; 4 = a required tool is missing or unusable.
# Optional lab checks (cluster, images) are reported as notes, not failures.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/preflight.sh

Checks required tools (docker, kind, kubectl, python3) and, if the lab cluster
exists, that it is reachable and passes the context guard. Read-only.
EOF
}

case "${1:-}" in
  -h | --help)
    usage
    exit 0
    ;;
  "") ;;
  *)
    usage >&2
    exit "$EX_USAGE"
    ;;
esac

failures=0
ok() { printf '  [ok]   %s\n' "$*"; }
bad() {
  printf '  [FAIL] %s\n' "$*"
  failures=$((failures + 1))
}
note() { printf '  [note] %s\n' "$*"; }

echo "Required tools"
ok "bash ${BASH_VERSION}"

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "docker daemon reachable ($(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'version unknown'))"
  else
    bad "docker is installed but the daemon is not reachable (start Docker Desktop / the docker service)"
  fi
else
  bad "docker not found (kind needs a container runtime; this kit was tested with Docker)"
fi

if command -v kind >/dev/null 2>&1; then
  ok "$(kind version 2>/dev/null | head -n 1)"
else
  bad "kind not found (https://kind.sigs.k8s.io/docs/user/quick-start/#installation)"
fi

if command -v kubectl >/dev/null 2>&1; then
  ok "kubectl client $(kubectl version --client -o yaml 2>/dev/null | awk '/gitVersion:/ {print $2; exit}')"
else
  bad "kubectl not found (https://kubernetes.io/docs/tasks/tools/)"
fi

if command -v python3 >/dev/null 2>&1 &&
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
  ok "$(python3 --version 2>&1)"
else
  bad "python3 >= 3.8 not found (needed by scripts/verify.sh)"
fi

echo
echo "Lab cluster (optional until you run scripts/cluster-up.sh)"
node_image="$(manifest_image "$LAB_ROOT/lab/kind-cluster.yaml")"
app_image="$(manifest_image "$LAB_ROOT/lab/base/app-template/deployment.yaml")"

if command -v kind >/dev/null 2>&1 && kind get clusters 2>/dev/null | grep -Fxq "$LAB_CLUSTER_NAME"; then
  ok "kind cluster '$LAB_CLUSTER_NAME' exists"
  if (lab_guard) 2>/dev/null; then
    ok "context guard passed ($LAB_CONTEXT, node $LAB_NODE_NAME)"
  else
    # Re-run unsuppressed to show the reason.
    (lab_guard) || true
    bad "context guard did not pass"
  fi
  if docker exec "$LAB_NODE_NAME" crictl images 2>/dev/null | grep -q "${app_image%%:*}.*${app_image##*:}"; then
    ok "app image $app_image is cached on the lab node"
  else
    note "app image $app_image is not cached on the lab node yet; the first scripts/reset.sh will download it"
  fi
else
  note "kind cluster '$LAB_CLUSTER_NAME' does not exist yet; run scripts/cluster-up.sh"
  if command -v docker >/dev/null 2>&1 && docker image inspect "$node_image" >/dev/null 2>&1; then
    note "node image is already cached locally (no node image download needed)"
  else
    note "node image will be downloaded by kind: ${node_image%%@*}"
  fi
fi

echo
if ((failures > 0)); then
  echo "Preflight: $failures required check(s) failed."
  exit "$EX_ENV"
fi
echo "Preflight: required checks passed."

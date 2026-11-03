#!/usr/bin/env bash
# All checks that need no cluster, no network, and change nothing outside a temp dir.
# Optional linters are used if present and reported as SKIPPED otherwise; a skip is
# never counted as a pass.
#
#   tests/run-static.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2
export PYTHONDONTWRITEBYTECODE=1

passed=0
failed=0
skipped=0

run() { # description command...
  local desc="$1"
  shift
  if out="$("$@" 2>&1)"; then
    echo "PASS  $desc"
    passed=$((passed + 1))
  else
    echo "FAIL  $desc"
    printf '%s\n' "$out" | sed 's/^/      | /'
    failed=$((failed + 1))
  fi
}
skip() {
  echo "SKIP  $1 ($2)"
  skipped=$((skipped + 1))
}

shell_files=(scripts/*.sh scripts/lib/common.sh tests/*.sh)

for f in "${shell_files[@]}"; do
  run "bash -n $f" bash -n "$f"
done

# Lint with a native shellcheck, else a locally cached image. Never pulls, never installs.
if command -v shellcheck >/dev/null 2>&1; then
  run "shellcheck (native)" shellcheck -x -P SCRIPTDIR "${shell_files[@]}"
elif command -v docker >/dev/null 2>&1 && docker image inspect koalaman/shellcheck:v0.10.0 >/dev/null 2>&1; then
  run "shellcheck v0.10.0 (local docker image, no network)" \
    docker run --rm --network none -v "$ROOT:/mnt:ro" -w /mnt koalaman/shellcheck:v0.10.0 -x -P SCRIPTDIR "${shell_files[@]}"
else
  skip "shellcheck" "not installed and no cached koalaman/shellcheck image"
fi

run "python compiles" python3 -c "
import ast, pathlib
for p in pathlib.Path('scripts/lib/verify.py'), *pathlib.Path('tests').glob('*.py'):
    ast.parse(p.read_text(), str(p))
"

if command -v black >/dev/null 2>&1; then
  run "black --check" black --check scripts tests
else
  skip "black" "not installed"
fi
if command -v yamllint >/dev/null 2>&1; then
  run "yamllint" yamllint -d relaxed lab
else
  skip "yamllint" "not installed"
fi

run "verifier unit tests" python3 -m unittest discover -s tests -p 'test_verify.py'
run "context guard tests (fake kubectl)" bash tests/test_guard.sh
run "rendered manifest checks" python3 tests/check_manifests.py
run "docs consistency checks" python3 tests/check_docs.py

echo
echo "static checks: $passed passed, $failed failed, $skipped skipped"
[[ "$failed" -eq 0 ]]

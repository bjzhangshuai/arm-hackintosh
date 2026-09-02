#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env

cd "$REPO_ROOT"
exec "$PYTHON_BIN" -m unittest discover -s tests -v

#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/require-debug-env.sh"
macvm_require_debug_env
exec python3 "$SCRIPT_DIR/../tools/vmapple_ean.py" "$@"

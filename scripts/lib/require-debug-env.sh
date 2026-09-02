#!/usr/bin/env bash

macvm_require_debug_env() {
  local marker="${MACVM_DEBUG_MARKER:-/etc/macvm-validation-guest}"

  if [[ "${MACVM_DEBUG_ENV_CONFIRMED:-}" != "YES" ]]; then
    echo "macvm: refusing to run outside an explicitly confirmed debug environment." >&2
    echo "macvm: set MACVM_DEBUG_ENV_CONFIRMED=YES only on the dedicated Linux x86_64 host." >&2
    return 78
  fi

  if [[ "$(uname -s)" != "Linux" || "$(uname -m)" != "x86_64" ]]; then
    echo "macvm: this command requires the dedicated Linux x86_64 debug host." >&2
    return 78
  fi

  if [[ ! -r "$marker" ]] || ! grep -qx 'MACVM_ISOLATED_VALIDATION_GUEST=YES' "$marker"; then
    echo "macvm: missing isolated validation guest marker: $marker" >&2
    return 78
  fi

  if ! command -v systemd-detect-virt >/dev/null 2>&1 || \
     ! systemd-detect-virt --vm --quiet; then
    echo "macvm: refusing to execute on a physical or unverified host." >&2
    return 78
  fi
}

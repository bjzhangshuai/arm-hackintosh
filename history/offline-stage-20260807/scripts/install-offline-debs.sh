#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEB_DIR="$BUNDLE_ROOT/packages/ubuntu-24.04-amd64/debs"

if [[ "${MACVM_TEST_VM_CONFIRMED:-}" != "YES" ]]; then
  echo "refusing to install: confirm a disposable test VM with MACVM_TEST_VM_CONFIRMED=YES" >&2
  exit 64
fi
if [[ "$(uname -s)" != Linux || "$(dpkg --print-architecture)" != amd64 ]]; then
  echo "offline packages require Linux amd64" >&2
  exit 69
fi
if [[ ! -r /etc/os-release ]]; then
  echo "cannot identify operating system" >&2
  exit 69
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != ubuntu || "${VERSION_ID:-}" != 24.04 ]]; then
  echo "offline packages are locked to Ubuntu 24.04 amd64, found ${ID:-unknown} ${VERSION_ID:-unknown}" >&2
  exit 69
fi
if ! compgen -G "$DEB_DIR/*.deb" >/dev/null; then
  echo "no DEB packages found in $DEB_DIR" >&2
  exit 66
fi

sudo apt-get install --no-download "$DEB_DIR"/*.deb


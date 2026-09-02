#!/usr/bin/env bash
set -euo pipefail

repo=${1:-/home/macvm/src/macvm/third_party/reims-vgpu}
root=$(cd "$(dirname "$0")/.." && pwd)
base=a9adcac950f73ac9b659f0f26e28d11fde3940e9

if [[ ! -d "$repo/.git" ]]; then
  echo "not a Reims git checkout: $repo" >&2
  exit 64
fi
if [[ $(git -C "$repo" rev-parse HEAD) != "$base" ]]; then
  echo "refusing unreviewed Reims base: $(git -C "$repo" rev-parse HEAD)" >&2
  exit 65
fi
if [[ -n $(git -C "$repo" status --short) ]]; then
  echo "refusing a dirty Reims checkout" >&2
  exit 66
fi

for patch in "$root"/patches/reims-vgpu/*.patch; do
  git -C "$repo" apply --check "$patch"
done
for patch in "$root"/patches/reims-vgpu/*.patch; do
  git -C "$repo" apply "$patch"
done

git -C "$repo" diff --check

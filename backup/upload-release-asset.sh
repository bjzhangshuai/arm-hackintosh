#!/usr/bin/env bash
# Data backup only: no build, test, probe, installation or VM execution.
set -euo pipefail
repo=bjzhangshuai/arm-hackintosh
release=backup-20260902-boot116
stage=/Users/jansurezhang/src/arm-hackintosh/release-staging/backup-20260902-boot116
[[ $# == 1 && "$1" != */* && -f "$stage/$1" ]] || exit 64
[[ "$(gh repo view "$repo" --json visibility --jq .visibility)" == PRIVATE ]] || exit 78
cd "$stage"
asset=$1
shasum -a 256 "$asset" > "$asset.sha256"
if [[ "$asset" == UniversalMac_26.6_25G72_Restore.ipsw ]]; then
  [[ "$(cut -d ' ' -f 1 "$asset.sha256")" == a8d59bdec11a16f704c1a41edc86461c77e71c790ac834a05266b9670287142c ]] || exit 65
fi
size=$(wc -c < "$asset")
if (( size >= 2147483648 )); then
  [[ ! -e "$asset.part-aa" ]] || { echo 'Existing parts require inspection before resuming' >&2; exit 78; }
  split -b 1900m "$asset" "$asset.part-"
  shasum -a 256 "$asset".part-* > "$asset.parts.sha256"
  for part in "$asset".part-*; do
    printf 'Uploading %s\n' "$part"
    gh release upload "$release" "$part" --repo "$repo"
  done
  gh release upload "$release" "$asset.parts.sha256" --repo "$repo"
else
  printf 'Uploading %s\n' "$asset"
  gh release upload "$release" "$asset" --repo "$repo"
fi
gh release upload "$release" "$asset.sha256" --repo "$repo"
printf 'Uploaded and hashed %s\n' "$asset"

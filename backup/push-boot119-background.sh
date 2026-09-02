#!/usr/bin/env bash
# Local backup controller: no compilation, tests, VM execution, or host changes.
# Start with nohup and a pinned commit; the controller survives the chat turn.
set -euo pipefail
root=/Users/jansurezhang/src/arm-hackintosh
stage="$root/release-staging/backup-20260903-boot119"
remote_repo=bjzhangshuai/arm-hackintosh
branch=dev/boot119-installer-20260903
tag=backup-20260903-boot119
[[ $# == 1 && "$1" =~ ^[0-9a-f]{40}$ ]] || exit 64
commit=$1
cd "$root"
mkdir -p "$stage"
mkdir "$stage/worker.lock" || { echo 'Backup worker lock already exists; inspect status first.' >&2; exit 78; }
finish() {
  rc=$?
  printf '%s exit=%s commit=%s\n' "$(date -u +%FT%TZ)" "$rc" "$commit" > "$stage/RESULT"
  rmdir "$stage/worker.lock"
}
trap finish EXIT
printf '%s\n' "$$" > "$stage/worker.pid"
printf '%s\n' "$commit" > "$stage/commit.txt"
retry() {
  local attempt
  for attempt in 1 2 3; do
    if "$@"; then return 0; fi
    [[ $attempt == 3 ]] && return 1
    sleep $((attempt * 5))
  done
}
[[ "$(git remote get-url origin)" == git@github.com:bjzhangshuai/arm-hackintosh.git ]] || exit 78
[[ "$(gh repo view "$remote_repo" --json visibility --jq .visibility)" == PRIVATE ]] || exit 78
[[ "$(git rev-parse "$branch")" == "$commit" ]] || exit 78
retry git push origin "$commit:refs/heads/$branch"
[[ "$(git ls-remote origin "refs/heads/$branch" | cut -f1)" == "$commit" ]] || exit 65
printf '%s\n' "$(date -u +%FT%TZ)" > "$stage/CODE_PUSHED"

if ! gh release view "$tag" --repo "$remote_repo" >/dev/null 2>&1; then
  retry gh release create "$tag" --repo "$remote_repo" --target "$commit" \
    --title 'Boot119: ARM64 macOS Tahoe installer GUI verified' \
    --notes-file backup/BOOT119-RELEASE-NOTES.md --prerelease --latest=false
fi
[[ "$(gh api "repos/$remote_repo/git/ref/tags/$tag" --jq .object.sha)" == "$commit" ]] || exit 65

ssh_options=( -o 'ProxyCommand=ssh -p 30022 -o BatchMode=yes -o ConnectTimeout=10 -W 127.0.0.1:30222 jansurezhang@192.168.8.123'
  -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null )
retry ssh "${ssh_options[@]}" macvm@validation-guest \
  'bash /home/macvm/src/macvm/backup/prepare-boot119-artifacts.sh'
remote_stage=/home/macvm/analysis/repository-backup-20260903-boot119
assets=( qemu-boot119-linux-x86_64.tar.gz linux-runtime-boot119.tar.gz
  boot119-test-build-evidence.tar.gz boot119-environment.tar.gz )
for asset in "${assets[@]}" SHA256SUMS; do
  retry scp "${ssh_options[@]}" "macvm@validation-guest:$remote_stage/$asset" "$stage/$asset.partial"
  mv "$stage/$asset.partial" "$stage/$asset"
done
(cd "$stage" && shasum -a 256 -c SHA256SUMS)
git archive --format=tar.gz --prefix=arm-hackintosh-boot119/ \
  -o "$stage/source-boot119.tar.gz.partial" "$commit"
mv "$stage/source-boot119.tar.gz.partial" "$stage/source-boot119.tar.gz"
cp evidence/boot119/screen-installer-first.png "$stage/screen-installer-first.png"
cp docs/boot119-installer-acceptance.md "$stage/boot119-installer-acceptance.md"
assets+=( source-boot119.tar.gz screen-installer-first.png boot119-installer-acceptance.md )
cd "$stage"
shasum -a 256 "${assets[@]}" > BOOT119-SHA256SUMS
assets+=( BOOT119-SHA256SUMS )
upload_verified() {
  local asset=$1 metadata expected size digest remote_size
  expected=$(shasum -a 256 "$asset" | cut -d ' ' -f1)
  size=$(wc -c < "$asset" | tr -d ' ')
  metadata=$(gh api "repos/$remote_repo/releases/tags/$tag" \
    --jq ".assets[] | select(.name == \"$asset\") | [.digest,.size] | @tsv") || return 1
  if [[ -z "$metadata" ]]; then
    gh release upload "$tag" "$asset" --repo "$remote_repo" || return 1
    metadata=$(gh api "repos/$remote_repo/releases/tags/$tag" \
      --jq ".assets[] | select(.name == \"$asset\") | [.digest,.size] | @tsv") || return 1
  fi
  IFS=$'\t' read -r digest remote_size <<< "$metadata"
  [[ "$digest" == "sha256:$expected" && "$remote_size" == "$size" ]] || {
    echo "Asset mismatch or missing digest: $asset; refusing to overwrite." >&2; return 1;
  }
  printf 'VERIFIED %s %s\n' "$asset" "$expected"
}
for asset in "${assets[@]}"; do retry upload_verified "$asset"; done
date -u +%FT%TZ > COMPLETE
printf 'Backup complete: https://github.com/%s/releases/tag/%s\n' "$remote_repo" "$tag"

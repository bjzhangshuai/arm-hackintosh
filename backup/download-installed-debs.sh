#!/usr/bin/env bash
# Download exact installed versions for an offline archive; never install/upgrade.
set -euo pipefail
[[ "$(hostname)" == macvm-validation && "$(uname -m)" == x86_64 ]] || exit 78
out=/home/macvm/analysis/repository-backup-20260902/debs
mkdir -p "$out"
cd "$out"
[[ ! -e attempted.tsv ]] || exit 78
dpkg-query -W -f='${binary:Package}\t${Version}\t${db:Status-Status}\n' > installed.tsv
while IFS=$'\t' read -r package version status; do
  [[ "$status" == installed ]] || continue
  printf '%s\t%s\n' "$package" "$version" >> attempted.tsv
  if timeout 120s apt-get download "$package=$version" >> download.log 2>&1; then
    printf '%s\t%s\n' "$package" "$version" >> downloaded.tsv
  else
    printf '%s\t%s\n' "$package" "$version" >> missing.tsv
  fi
done < installed.tsv
shopt -s nullglob
debs=( ./*.deb )
(( ${#debs[@]} > 0 )) || exit 69
sha256sum "${debs[@]}" > SHA256SUMS
tar -I 'zstd -T1 -3' -cf ../artifacts/ubuntu-26.04-installed-debs.tar.zst \
  installed.tsv attempted.tsv downloaded.tsv download.log SHA256SUMS "${debs[@]}" \
  $( [[ -e missing.tsv ]] && printf 'missing.tsv' )
date -u +%FT%TZ > PREPARED

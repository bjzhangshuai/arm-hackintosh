#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 INPUT_AUX OUTPUT_TRIMMED_AUX" >&2
  exit 64
fi

input=$1
output=$2
if [[ ! -f "$input" ]]; then
  echo "missing AUX input: $input" >&2
  exit 66
fi
if [[ -e "$output" ]]; then
  echo "refusing to overwrite existing output: $output" >&2
  exit 73
fi
if (( $(stat -c %s "$input") <= 0x4000 )); then
  echo "AUX input is too small to trim: $input" >&2
  exit 65
fi

mkdir -p "$(dirname "$output")"
temporary="${output}.partial.$$"
trap 'rm -f -- "$temporary"' EXIT
dd if="$input" of="$temporary" bs=$((0x4000)) skip=1 status=progress conv=fsync
mv -- "$temporary" "$output"
trap - EXIT


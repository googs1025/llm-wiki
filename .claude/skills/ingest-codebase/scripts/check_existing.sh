#!/usr/bin/env bash
# check_existing.sh — report any pre-existing output files for a given slug.
# Usage: check_existing.sh <slug>
# Env: WIKI_ROOT — wiki root directory (default: $PWD)
# Exit codes:
#   0 — no conflicts; no output
#   1 — conflicts; absolute file paths printed, one per line
#   2 — usage / bad input
set -uo pipefail

slug="${1:-}"
if [[ -z "$slug" ]]; then
  echo "usage: $0 <slug>" >&2
  exit 2
fi

wiki_root="${WIKI_ROOT:-$PWD}"
raw_file="$wiki_root/raw/${slug}-architecture-analysis.md"
wiki_file="$wiki_root/wiki/sources/src-${slug}-architecture.md"

conflicts=()
[[ -f "$raw_file"  ]] && conflicts+=("$raw_file")
[[ -f "$wiki_file" ]] && conflicts+=("$wiki_file")

if (( ${#conflicts[@]} > 0 )); then
  printf '%s\n' "${conflicts[@]}"
  exit 1
fi
exit 0

#!/usr/bin/env bash
# clone_or_locate.sh — resolve <path-or-github-url> to an absolute repo path.
#   Local path → echo abspath
#   GitHub URL → git clone into /tmp/ingest-codebase-<hash>/ if not yet present, echo path
# Exit codes:
#   0 — path printed
#   2 — usage / invalid input / clone failure
set -uo pipefail

input="${1:-}"
if [[ -z "$input" ]]; then
  echo "usage: $0 <path-or-url>" >&2
  exit 2
fi

is_github_url() {
  [[ "$1" =~ ^(https?://github\.com/|git@github\.com:) ]]
}

if is_github_url "$input"; then
  hash=$(printf '%s' "$input" | shasum | cut -c1-8)
  dest="/tmp/ingest-codebase-${hash}"
  if [[ ! -d "$dest/.git" ]]; then
    rm -rf "$dest"
    # --depth 100: enough history for code-explorer to see recent evolution
    # without paying for huge mono-repo histories. Raise if you need older commits.
    if ! git clone --depth 100 "$input" "$dest" >&2; then
      echo "error: git clone failed for $input" >&2
      exit 2
    fi
  fi
  (cd "$dest" && pwd)
  exit 0
fi

if [[ -d "$input" ]]; then
  (cd "$input" && pwd)
  exit 0
fi

echo "error: not a github URL and not an existing directory: $input" >&2
exit 2

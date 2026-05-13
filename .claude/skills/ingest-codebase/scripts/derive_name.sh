#!/usr/bin/env bash
# derive_name.sh — derive a project slug from a local path or GitHub URL.
# Usage: derive_name.sh <path-or-url>
# Exit codes:
#   0 — slug printed, unambiguous
#   1 — slug printed, but generic/ambiguous (caller should disambiguate)
#   2 — usage / invalid input
set -uo pipefail

input="${1:-}"
if [[ -z "$input" ]]; then
  echo "usage: $0 <path-or-url>" >&2
  exit 2
fi

slug=""

# Match common GitHub URL forms:
#   https://github.com/<owner>/<repo>[.git][/]
#   http://github.com/...
#   git@github.com:<owner>/<repo>[.git][/]
if [[ "$input" =~ ^(https?://github\.com/|git@github\.com:)([^/]+)/([^/]+)/?$ ]]; then
  slug="${BASH_REMATCH[3]}"
  slug="${slug%.git}"
elif [[ -d "$input" ]]; then
  slug="$(basename "$(cd "$input" && pwd)")"
else
  echo "error: not a github URL and not an existing directory: $input" >&2
  exit 2
fi

# Slugs that aren't distinctive enough on their own — caller should disambiguate.
case "$slug" in
  repo|code|src|main|master|app|project|tmp|test)
    echo "$slug"
    exit 1
    ;;
esac

echo "$slug"
exit 0

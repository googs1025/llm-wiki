#!/usr/bin/env bash
# Tests for check_existing.sh
set -uo pipefail
SCRIPT="$(cd "$(dirname "$0")" && pwd)/check_existing.sh"
fails=0

assert_exit() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "PASS: $label (exit $actual)"
  else
    echo "FAIL: $label — expected exit [$expected] got [$actual]"
    fails=$((fails+1))
  fi
}

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    echo "PASS: $label"
  else
    echo "FAIL: $label — [$haystack] missing [$needle]"
    fails=$((fails+1))
  fi
}

tmp=$(mktemp -d -t check-existing-test-XXXX)
mkdir -p "$tmp/raw" "$tmp/wiki/sources"
export WIKI_ROOT="$tmp"

# Case 1: No files → exit 0, no output
out=$("$SCRIPT" "fresh-slug" 2>/dev/null); rc=$?
assert_exit "no conflicts" "0" "$rc"
[[ -z "$out" ]] && echo "PASS: no output on clean" || { echo "FAIL: unexpected output [$out]"; fails=$((fails+1)); }

# Case 2: Raw exists → exit 1, output mentions raw path
touch "$tmp/raw/has-raw-architecture-analysis.md"
out=$("$SCRIPT" "has-raw" 2>/dev/null); rc=$?
assert_exit "raw exists" "1" "$rc"
assert_contains "raw mentioned" "raw/has-raw-architecture-analysis.md" "$out"

# Case 3: Both exist → exit 1, output mentions both
touch "$tmp/wiki/sources/src-both-architecture.md"
touch "$tmp/raw/both-architecture-analysis.md"
out=$("$SCRIPT" "both" 2>/dev/null); rc=$?
assert_exit "both exist" "1" "$rc"
assert_contains "both raw" "raw/both-architecture-analysis.md" "$out"
assert_contains "both wiki" "wiki/sources/src-both-architecture.md" "$out"

# Case 4: Missing slug → exit 2
out=$("$SCRIPT" 2>/dev/null); rc=$?
assert_exit "missing arg" "2" "$rc"

rm -rf "$tmp"
echo "---"
if (( fails == 0 )); then echo "ALL PASS"; exit 0; else echo "$fails FAIL"; exit 1; fi

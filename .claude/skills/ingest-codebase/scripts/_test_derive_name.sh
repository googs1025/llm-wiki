#!/usr/bin/env bash
# Tests for derive_name.sh
set -uo pipefail
SCRIPT="$(cd "$(dirname "$0")" && pwd)/derive_name.sh"
fails=0

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "PASS: $label"
  else
    echo "FAIL: $label — expected [$expected] got [$actual]"
    fails=$((fails+1))
  fi
}

assert_exit() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "PASS: $label (exit $actual)"
  else
    echo "FAIL: $label — expected exit [$expected] got [$actual]"
    fails=$((fails+1))
  fi
}

# Case 1: HTTPS GitHub URL → repo name
out=$("$SCRIPT" "https://github.com/thedotmack/claude-mem"); rc=$?
assert_eq "https github url"          "claude-mem" "$out"
assert_exit "https github url exit"   "0"          "$rc"

# Case 2: HTTPS GitHub URL with .git suffix
out=$("$SCRIPT" "https://github.com/thedotmack/claude-mem.git")
assert_eq "https github url .git"     "claude-mem" "$out"

# Case 3: SSH GitHub URL
out=$("$SCRIPT" "git@github.com:thedotmack/claude-mem.git")
assert_eq "ssh github url"            "claude-mem" "$out"

# Case 4: Trailing slash
out=$("$SCRIPT" "https://github.com/thedotmack/claude-mem/")
assert_eq "trailing slash"            "claude-mem" "$out"

# Case 5: Local directory
tmpdir=$(mktemp -d -t derive-name-test-XXXX)
mkdir -p "$tmpdir/my-cool-project"
out=$("$SCRIPT" "$tmpdir/my-cool-project"); rc=$?
assert_eq "local dir"                 "my-cool-project" "$out"
assert_exit "local dir exit"          "0"               "$rc"
rm -rf "$tmpdir"

# Case 6: Ambiguous generic name → slug printed but exit 1
tmpdir=$(mktemp -d -t derive-name-test-XXXX)
mkdir -p "$tmpdir/repo"
out=$("$SCRIPT" "$tmpdir/repo"); rc=$?
assert_eq "ambiguous slug printed"    "repo" "$out"
assert_exit "ambiguous exit code"     "1"    "$rc"
rm -rf "$tmpdir"

# Case 7: Missing arg
out=$("$SCRIPT" 2>/dev/null); rc=$?
assert_exit "missing arg exit"        "2"    "$rc"

# Case 8: Nonexistent path that isn't a URL
out=$("$SCRIPT" "/no/such/path" 2>/dev/null); rc=$?
assert_exit "bad input exit"          "2"    "$rc"

echo "---"
if (( fails == 0 )); then echo "ALL PASS"; exit 0; else echo "$fails FAIL"; exit 1; fi

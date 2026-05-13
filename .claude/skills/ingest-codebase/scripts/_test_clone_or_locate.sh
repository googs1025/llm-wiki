#!/usr/bin/env bash
# Tests for clone_or_locate.sh
# Notes: GitHub-URL test case is skipped by default to avoid network during CI-style runs.
#        Set RUN_NETWORK_TESTS=1 to enable it.
set -uo pipefail
SCRIPT="$(cd "$(dirname "$0")" && pwd)/clone_or_locate.sh"
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

# Case 1: Local absolute path resolves to its abspath
tmpdir=$(mktemp -d -t clone-locate-test-XXXX)
mkdir -p "$tmpdir/myrepo"
out=$("$SCRIPT" "$tmpdir/myrepo" 2>/dev/null); rc=$?
assert_eq "local abs path"   "$(cd "$tmpdir/myrepo" && pwd)" "$out"
assert_exit "local abs exit" "0"                              "$rc"

# Case 2: Local relative path resolves to absolute
pushd "$tmpdir" >/dev/null
out=$("$SCRIPT" "./myrepo" 2>/dev/null); rc=$?
popd >/dev/null
assert_eq "local rel path"   "$(cd "$tmpdir/myrepo" && pwd)" "$out"

rm -rf "$tmpdir"

# Case 3: Nonexistent path → exit 2
out=$("$SCRIPT" "/no/such/path" 2>/dev/null); rc=$?
assert_exit "bad path exit" "2" "$rc"

# Case 4: Missing arg → exit 2
out=$("$SCRIPT" 2>/dev/null); rc=$?
assert_exit "missing arg exit" "2" "$rc"

# Case 5: GitHub URL (network — opt in)
if [[ "${RUN_NETWORK_TESTS:-0}" == "1" ]]; then
  url="https://github.com/octocat/Hello-World"
  out=$("$SCRIPT" "$url" 2>/dev/null); rc=$?
  if [[ -d "$out" && -d "$out/.git" ]]; then
    echo "PASS: github clone produced a git repo at $out"
  else
    echo "FAIL: github clone — got [$out]"
    fails=$((fails+1))
  fi
  out2=$("$SCRIPT" "$url" 2>/dev/null)
  assert_eq "github clone idempotent" "$out" "$out2"
fi

echo "---"
if (( fails == 0 )); then echo "ALL PASS"; exit 0; else echo "$fails FAIL"; exit 1; fi

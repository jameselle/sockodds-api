#!/usr/bin/env bash
# Run every example (curl, Python, JavaScript) against the local mock and compare the output
# with tests/expected/. No key and no network needed: the mock serves invented sample data.
#
#   tests/run_examples.sh            # check
#   tests/run_examples.sh --update   # rewrite tests/expected/ from the current output
#
# Needs python3 (3.8+), node (18+), curl (7.76+) and jq.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXPECTED="$ROOT/tests/expected"
UPDATE="${1:-}"

PORT_FILE="$(mktemp)"
python3 "$ROOT/mock/server.py" --port 0 >"$PORT_FILE" &
MOCK_PID=$!
trap 'status=$?; kill $MOCK_PID 2>/dev/null || true; wait $MOCK_PID 2>/dev/null || true; rm -f "$PORT_FILE"; exit $status' EXIT
for _ in $(seq 50); do [ -s "$PORT_FILE" ] && break; sleep 0.1; done
export SOCKODDS_BASE_URL="$(sed -n 's/.* on //p' "$PORT_FILE")"
export SOCKODDS_API_KEY="sample-key-not-real"   # the mock accepts any bearer key; this is not a real key
export SOCKODDS_LEAGUE="sample_league"
unset SOCKODDS_EVENT_ID

# name | expected file | command
CASES=(
  "curl first-request|curl-first-request|$ROOT/examples/curl/first-request.sh"
  "curl odds-comparison|curl-odds-comparison|$ROOT/examples/curl/odds-comparison.sh"
  "curl arbitrage|curl-arbitrage|$ROOT/examples/curl/arbitrage.sh"
  "curl line-movement|curl-line-movement|$ROOT/examples/curl/line-movement.sh ev_0000000000a1"
  "curl settle-bets|curl-settle-bets|$ROOT/examples/curl/settle-bets.sh ev_0000000000b1"
  "python first_request|first-request|python3 $ROOT/examples/python/first_request.py"
  "python odds_comparison|odds-comparison|python3 $ROOT/examples/python/odds_comparison.py"
  "python arbitrage|arbitrage|python3 $ROOT/examples/python/arbitrage.py"
  "python line_movement|line-movement|python3 $ROOT/examples/python/line_movement.py ev_0000000000a1"
  "python settle_bets|settle-bets|python3 $ROOT/examples/python/settle_bets.py ev_0000000000b1"
  "node first-request|first-request|node $ROOT/examples/javascript/first-request.mjs"
  "node odds-comparison|odds-comparison|node $ROOT/examples/javascript/odds-comparison.mjs"
  "node arbitrage|arbitrage|node $ROOT/examples/javascript/arbitrage.mjs"
  "node line-movement|line-movement|node $ROOT/examples/javascript/line-movement.mjs ev_0000000000a1"
  "node settle-bets|settle-bets|node $ROOT/examples/javascript/settle-bets.mjs ev_0000000000b1"
)

pass=0 fail=0
for case in "${CASES[@]}"; do
  IFS='|' read -r name file command <<<"$case"
  if ! output="$($command 2>&1)"; then
    echo "FAIL $name (exit code)"; printf '%s\n' "$output" | sed 's/^/     /'; fail=$((fail + 1)); continue
  fi
  if [ "$UPDATE" = "--update" ] && [[ "$name" != node* ]]; then
    printf '%s\n' "$output" >"$EXPECTED/$file.txt"
  fi
  if diff -u "$EXPECTED/$file.txt" <(printf '%s\n' "$output") >/dev/null; then
    echo "ok   $name"; pass=$((pass + 1))
  else
    echo "FAIL $name (output differs)"; diff -u "$EXPECTED/$file.txt" <(printf '%s\n' "$output") | sed 's/^/     /' || true
    fail=$((fail + 1))
  fi
done

# Every example must refuse to run without a key, and report an API error instead of crashing.
if SOCKODDS_API_KEY= python3 "$ROOT/examples/python/first_request.py" >/dev/null 2>&1; then
  echo "FAIL python runs without a key"; fail=$((fail + 1)); else echo "ok   python refuses to run without a key"; pass=$((pass + 1)); fi
if SOCKODDS_API_KEY= node "$ROOT/examples/javascript/first-request.mjs" >/dev/null 2>&1; then
  echo "FAIL node runs without a key"; fail=$((fail + 1)); else echo "ok   node refuses to run without a key"; pass=$((pass + 1)); fi
for command in "$ROOT/examples/curl/odds-comparison.sh ev_0000000000zz" \
               "python3 $ROOT/examples/python/odds_comparison.py ev_0000000000zz" \
               "node $ROOT/examples/javascript/odds-comparison.mjs ev_0000000000zz"; do
  if output="$($command 2>&1)" || ! grep -q "HTTP 404" <<<"$output"; then
    echo "FAIL ${command##*/} does not report a 404 problem"; fail=$((fail + 1))
  else
    echo "ok   ${command##*/} reports a 404 problem"; pass=$((pass + 1))
  fi
done

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]

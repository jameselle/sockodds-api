#!/usr/bin/env bash
# Compare one game's winner prices across every bookmaker and print the best price for each side.
#
#   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
#   ./odds-comparison.sh [EVENT_ID]
#
# With no EVENT_ID it uses the next game in SOCKODDS_LEAGUE (default nfl). Needs curl 7.76+ and jq.
# Mirrors https://sockodds.com/docs/examples/odds-comparison/
set -euo pipefail
: "${SOCKODDS_API_KEY:?Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/}"
BASE="${SOCKODDS_BASE_URL:-https://api.sockodds.com/v1}"
LEAGUE="${SOCKODDS_LEAGUE:-nfl}"
get() {
  local body
  if ! body="$(curl -sS --fail-with-body -H "Authorization: Bearer $SOCKODDS_API_KEY" -H "Accept: application/json" "$1")"; then
    # errors are application/problem+json: print the status, title and detail, then stop
    { jq -r '"HTTP \(.status) from \(.instance): \(.title): \(.detail)"' <<<"$body" 2>/dev/null || printf '%s\n' "$body"; } >&2
    exit 1
  fi
  printf '%s\n' "$body"
}

EVENT_ID="${1:-${SOCKODDS_EVENT_ID:-}}"
if [ -z "$EVENT_ID" ]; then
  NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  EVENT_ID="$(get "$BASE/events?league=$LEAGUE&starts_after=$NOW&limit=1" | jq -r '.data[0].id // empty')"
  [ -n "$EVENT_ID" ] || { echo "No upcoming $LEAGUE game. Pass an event id or set SOCKODDS_LEAGUE." >&2; exit 1; }
fi

# One request returns every bookmaker's quotes; each outcome's prices are sorted best first.
get "$BASE/events/$EVENT_ID/odds?markets=winner" | jq -r '
  .data as $e
  | ([$e.markets[] | select(.key == "winner" and .period == "full")][0].outcomes // []) as $outcomes
  | "\($e.name), winner (full game)",
    ($e.participants[] | .role as $role | .identity.name as $name
      | ([$outcomes[] | select(.side == $role)][0]) as $o
      | if $o == null then "  \($name): no current price"
        else "  \($o.name): best \($o.prices[0].decimal_odds) at \($o.prices[0].bookmaker), seen \($o.prices[0].observed_at), \($o.prices | length) bookmaker(s) quoting",
             "    all: \([$o.prices[] | "\(.bookmaker) \(.decimal_odds)"] | join(", "))"
        end)'

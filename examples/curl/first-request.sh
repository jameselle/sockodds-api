#!/usr/bin/env bash
# Your first SockOdds requests: the sports your key can read, then the next game's winner prices.
#
#   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
#   ./first-request.sh
#
# Optional: SOCKODDS_LEAGUE (default nfl), SOCKODDS_BASE_URL (default https://api.sockodds.com/v1).
# Needs curl 7.76+ and jq.
set -euo pipefail
: "${SOCKODDS_API_KEY:?Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/}"
BASE="${SOCKODDS_BASE_URL:-https://api.sockodds.com/v1}"
LEAGUE="${SOCKODDS_LEAGUE:-nfl}"

# The key goes in the Authorization header only, never in the URL.
get() {
  local body
  if ! body="$(curl -sS --fail-with-body -H "Authorization: Bearer $SOCKODDS_API_KEY" -H "Accept: application/json" "$1")"; then
    # errors are application/problem+json: print the status, title and detail, then stop
    { jq -r '"HTTP \(.status) from \(.instance): \(.title): \(.detail)"' <<<"$body" 2>/dev/null || printf '%s\n' "$body"; } >&2
    exit 1
  fi
  printf '%s\n' "$body"
}

# 1. The sports your key can read (the raw response, so you can see the {data, meta, links} envelope).
get "$BASE/sports" | jq .

# 2. The next game's winner market, every bookmaker in your plan, best price first.
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
get "$BASE/odds?league=$LEAGUE&markets=winner&limit=1&starts_after=$NOW" | jq -r '
  if (.data | length) == 0 then "No upcoming game has winner prices right now. Try another SOCKODDS_LEAGUE."
  else .data[0] as $g
    | "Next game: \($g.name), starts \($g.scheduled_start) (\($g.status))",
      ($g.markets[] | select(.key == "winner" and .period == "full") | .outcomes[]
        | "  \(.name): best \(.prices[0].decimal_odds) at \(.prices[0].bookmaker), \(.prices | length) bookmaker(s) quoting, seen \(.prices[0].observed_at)")
  end'

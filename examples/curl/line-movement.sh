#!/usr/bin/env bash
# Track line movement: how each bookmaker's winner price moved over a window, from recorded history.
#
#   export SOCKODDS_API_KEY="your-key"     # Pro plan (history): https://sockodds.com/pricing/
#   ./line-movement.sh EVENT_ID [FROM TO]
#
# FROM and TO are UTC times such as 2026-12-05T00:00:00Z; the default is the last 8 hours (at most
# 24). Needs curl 7.76+ and jq. Mirrors https://sockodds.com/docs/examples/line-movement/
set -euo pipefail
: "${SOCKODDS_API_KEY:?Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/}"
BASE="${SOCKODDS_BASE_URL:-https://api.sockodds.com/v1}"
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
[ -n "$EVENT_ID" ] || { echo "Usage: ./line-movement.sh EVENT_ID [FROM TO]" >&2; exit 1; }
FROM="${2:-$(jq -rn 'now - 8 * 3600 | strftime("%Y-%m-%dT%H:%M:%SZ")')}"
TO="${3:-$(jq -rn 'now | strftime("%Y-%m-%dT%H:%M:%SZ")')}"

# Read every page of history, then keep the first and latest price per bookmaker, side and period.
url="$BASE/odds/history?event_id=$EVENT_ID&from=$FROM&to=$TO&markets=winner&limit=250"
rows="[]"
while [ -n "$url" ]; do
  page="$(get "$url")"
  rows="$(jq -c --argjson acc "$rows" '$acc + .data' <<<"$page")"
  url="$(jq -r '.links.next // empty' <<<"$page")"
done

jq -r '
  [.[] | select(.decimal_odds != null)]          # a withdrawal has no price
  | group_by("\(.bookmaker)|\(.outcome.side)|\(.market.period)")
  | if length == 0 then "No recorded winner prices in this window." else .[]
    | first as $f | last as $l
    | "\($f.bookmaker)  \($f.outcome.name): \($f.decimal_odds) to \($l.decimal_odds) (\(($l.decimal_odds - $f.decimal_odds) * 100 | round / 100)), changes: \(map(select(.kind == "changed")) | length), latest \($l.observed_at)"
    end' <<<"$rows"

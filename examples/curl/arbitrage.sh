#!/usr/bin/env bash
# Check the market margin at the best prices: sum 1/price over the best price on every side.
#
#   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
#   ./arbitrage.sh
#
# Reads every upcoming game in SOCKODDS_LEAGUE (default nfl), following links.next. A sum under 1
# is rare and short lived with real prices: treat it as a measure of how tight a market is, not a
# source of profit. Needs curl 7.76+ and jq. Mirrors https://sockodds.com/docs/examples/arbitrage/
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

# Every item of a list route as one JSON array: follow links.next unchanged until it is null.
get_all() {
  local url="$1" page items="[]"
  while [ -n "$url" ]; do
    page="$(get "$url")"
    items="$(jq -c --argjson acc "$items" '$acc + .data' <<<"$page")"
    url="$(jq -r '.links.next // empty' <<<"$page")"
  done
  printf '%s' "$items"
}

# Which sides make up each market in this league (from the catalogue).
SIDES="$(get_all "$BASE/markets?league=$LEAGUE&limit=100" | jq -c 'map(select(.sides | type == "array") | {(.key): .sides}) | add // {}')"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

get_all "$BASE/odds?league=$LEAGUE&limit=25&starts_after=$NOW" | jq -r --argjson sides "$SIDES" '
  .[] | .name, (.markets[]
    | . as $m
    | ([.outcomes[] | {(.side): .}] | add) as $by
    | $sides[$m.key] as $keys
    | if $keys == null or ([$keys[] | $by[.].prices[0]? // null] | any(. == null))
      then "  \($m.name) (\($m.period)): skipped, not every side has a current price"
      else ([$keys[] | 1 / $by[.].prices[0].decimal_odds] | add) as $sum
        | "  \($m.name)\(if $by[$keys[0]].line == null then "" else " \($by[$keys[0]].line)" end) (\($m.period))",
          ($keys[] | "    \(.): \($by[.].prices[0].decimal_odds) at \($by[.].prices[0].bookmaker)"),
          "    sum \($sum * 10000 | round / 10000), margin \(($sum - 1) * 10000 | round / 100)%, \(if $sum < 1 then "under 1: check every price is still up" else "over 1: no arbitrage" end)"
      end)'

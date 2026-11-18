#!/usr/bin/env bash
# Settle bets from graded results: each bet's verdict and return, including dead heats and pending markets.
#
#   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
#   ./settle-bets.sh EVENT_ID
#
# The bets below are SAMPLE bets (invented stakes and prices). An outcome with no verdict yet is
# pending, never lost. Needs curl 7.76+ and jq. Mirrors https://sockodds.com/docs/examples/settle-bets/
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
[ -n "$EVENT_ID" ] || { echo "Usage: ./settle-bets.sh EVENT_ID" >&2; exit 1; }

BETS='[
  {"market": "winner", "period": "full", "side": "home", "line": null, "stake": 10, "price": 1.85},
  {"market": "winner", "period": "half_1", "side": "home", "line": null, "stake": 10, "price": 2.10},
  {"market": "handicap", "period": "full", "side": "away", "line": 3.5, "stake": 20, "price": 1.90},
  {"market": "total_points", "period": "full", "side": "over", "line": 45.5, "stake": 10, "price": 1.87}
]'

get "$BASE/results?event_id=$EVENT_ID" | jq -r --argjson bets "$BETS" '
  def money: . * 100 | round / 100;
  .data as $results
  | [$results[].outcomes[]] as $graded
  | (if ($results | length) > 0 then ($results[-1] | "\(.event.name): \(.status), \(.settlement), markets pending: \(.pending_markets)")
     else "no graded results yet" end),
    ($bets[] | . as $b
      | "\(.market) (\(.period)) \(.side)\(if .line == null then "" else " \(.line)" end) at \(.price)" as $label
      | ([$graded[] | select(.market.key == $b.market and .market.period == $b.period and .side == $b.side and .line == $b.line)][0]) as $o
      | if $o == null then "  \($label): pending, stake \($b.stake) still open"
        else ({won: ($b.stake * $b.price), lost: 0, void: $b.stake,
               dead_heat: ($b.stake * ($o.dead_heat_factor // 0) * $b.price),
               half_won: ($b.stake / 2 * $b.price + $b.stake / 2), half_lost: ($b.stake / 2)}[$o.verdict]) as $r
          | "  \($label): \($o.verdict), stake \($b.stake), returns \($r | money), profit \($r - $b.stake | money)"
        end)'

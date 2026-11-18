#!/usr/bin/env python3
"""Settle bets from graded results: each bet's verdict and return, including dead heats and pending markets.

    export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
    python3 settle_bets.py EVENT_ID

The bets below are SAMPLE bets. In your code they come from your own database, stored with the
event id (and ideally the outcome id) when each bet was placed. An outcome with no verdict yet is
pending, never lost. Python 3.8+, standard library only.
Mirrors https://sockodds.com/docs/examples/settle-bets/
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("SOCKODDS_BASE_URL", "https://api.sockodds.com/v1").rstrip("/")
KEY = os.environ.get("SOCKODDS_API_KEY")

# Sample bets (invented stakes and prices).
BETS = [
    {"market": "winner", "period": "full", "side": "home", "line": None, "stake": 10, "price": 1.85},
    {"market": "winner", "period": "half_1", "side": "home", "line": None, "stake": 10, "price": 2.10},
    {"market": "handicap", "period": "full", "side": "away", "line": 3.5, "stake": 20, "price": 1.90},
    {"market": "total_points", "period": "full", "side": "over", "line": 45.5, "stake": 10, "price": 1.87},
]


def get(path, **params):
    """GET a SockOdds route (or a full links.next URL) and return the JSON body."""
    url = path if path.startswith("http") else BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + KEY, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:  # errors are application/problem+json
        try:
            problem = json.load(error)
            message = f"{problem.get('title')}: {problem.get('detail')}"
        except ValueError:
            message = error.reason
        sys.exit(f"HTTP {error.code} from {url.split('?')[0]}: {message}")


def returned(bet, outcome):
    stake, price, verdict = bet["stake"], bet["price"], outcome["verdict"]
    if verdict == "won":
        return stake * price
    if verdict == "void":
        return stake
    if verdict == "dead_heat":  # paid at dead_heat_factor of the stake, the rest lost
        return stake * outcome["dead_heat_factor"] * price
    if verdict == "half_won":  # Asian quarter line: half won at the price, half refunded
        return stake / 2 * price + stake / 2
    if verdict == "half_lost":  # half refunded, half lost
        return stake / 2
    return 0.0  # lost


def main():
    if not KEY:
        sys.exit("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/")
    event_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SOCKODDS_EVENT_ID")
    if not event_id:
        sys.exit("Usage: python3 settle_bets.py EVENT_ID")

    results = get("/results", event_id=event_id)["data"]
    # One result per event. It gains outcomes as more markets settle, so read it again later.
    graded = [outcome for result in results for outcome in result["outcomes"]]
    if results:
        last = results[-1]
        print(f"{last['event']['name']}: {last['status']}, {last['settlement']}, markets pending: {last['pending_markets']}")
    else:
        print(f"{event_id}: no graded results yet")

    for bet in BETS:
        line = "" if bet["line"] is None else f" {bet['line']}"
        label = f"{bet['market']} ({bet['period']}) {bet['side']}{line} at {bet['price']:.2f}"
        outcome = next(
            (o for o in graded
             if o["market"]["key"] == bet["market"] and o["market"]["period"] == bet["period"]
             and o["side"] == bet["side"] and o["line"] == bet["line"]),
            None,
        )
        if outcome is None:
            print(f"  {label}: pending, stake {bet['stake']:.2f} still open")
            continue
        back = returned(bet, outcome)
        print(f"  {label}: {outcome['verdict']}, stake {bet['stake']:.2f}, "
              f"returns {back:.2f}, profit {back - bet['stake']:.2f}")


if __name__ == "__main__":
    main()

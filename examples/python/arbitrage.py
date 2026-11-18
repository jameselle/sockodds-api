#!/usr/bin/env python3
"""Check the market margin at the best prices: sum 1/price over the best price on every side.

    export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
    python3 arbitrage.py

Reads every upcoming game in SOCKODDS_LEAGUE (default nfl), following links.next. A sum under 1
means the best prices carried no margin at the moment they were seen. With real prices that is
rare and short lived, prices move, and bookmakers may limit accounts: treat this as a measure of
how tight a market is, not a source of profit.
Python 3.8+, standard library only. Mirrors https://sockodds.com/docs/examples/arbitrage/
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE = os.environ.get("SOCKODDS_BASE_URL", "https://api.sockodds.com/v1").rstrip("/")
KEY = os.environ.get("SOCKODDS_API_KEY")
LEAGUE = os.environ.get("SOCKODDS_LEAGUE", "nfl")


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


def get_all(path, **params):
    """Every item of a list route: follow links.next unchanged until it is null."""
    body = get(path, **params)
    rows = list(body["data"])
    while body["links"]["next"]:
        body = get(body["links"]["next"])
        rows.extend(body["data"])
    return rows


def main():
    if not KEY:
        sys.exit("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/")

    # Which sides make up each market in this league (from the catalogue; cache this in your code).
    sides = {m["key"]: m["sides"] for m in get_all("/markets", league=LEAGUE, limit=100) if isinstance(m.get("sides"), list)}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for event in get_all("/odds", league=LEAGUE, limit=25, starts_after=now):
        print(event["name"])
        for market in event["markets"]:
            outcomes = {outcome["side"]: outcome for outcome in market["outcomes"]}
            keys = sides.get(market["key"])
            if not keys or not all(side in outcomes and outcomes[side]["prices"] for side in keys):
                print(f"  {market['name']} ({market['period']}): skipped, not every side has a current price")
                continue
            first = outcomes[keys[0]]
            label = market["name"] + ("" if first["line"] is None else f" {first['line']}") + f" ({market['period']})"
            total = sum(1 / outcomes[side]["prices"][0]["decimal_odds"] for side in keys)
            print(f"  {label}")
            for side in keys:
                best = outcomes[side]["prices"][0]  # prices are sorted best first
                print(f"    {side}: {best['decimal_odds']:.2f} at {best['bookmaker']}")
            note = "under 1: check every price is still up" if total < 1 else "over 1: no arbitrage"
            print(f"    sum {total:.4f}, margin {(total - 1) * 100:.2f}%, {note}")


if __name__ == "__main__":
    main()

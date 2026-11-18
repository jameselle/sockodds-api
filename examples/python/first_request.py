#!/usr/bin/env python3
"""Your first SockOdds requests: the sports your key can read, then the next game's winner prices.

    export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
    python3 first_request.py

Optional: SOCKODDS_LEAGUE (default nfl), SOCKODDS_BASE_URL (default https://api.sockodds.com/v1).
Python 3.8+, standard library only.
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


def main():
    if not KEY:
        sys.exit("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/")

    print("Sports your key can read:")
    for sport in get("/sports")["data"]:
        print(f"  {sport['key']}: {sport['name']}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    games = get("/odds", league=LEAGUE, markets="winner", limit=1, starts_after=now)["data"]
    if not games:
        print(f"\nNo upcoming {LEAGUE} game has winner prices right now. Try another SOCKODDS_LEAGUE.")
        return
    game = games[0]
    print(f"\nNext {LEAGUE} game: {game['name']}, starts {game['scheduled_start']} ({game['status']})")
    for market in game["markets"]:
        if market["key"] != "winner" or market["period"] != "full":
            continue
        for outcome in market["outcomes"]:
            best = outcome["prices"][0]  # prices are sorted best first
            print(
                f"  {outcome['name']}: best {best['decimal_odds']:.2f} at {best['bookmaker']}, "
                f"{len(outcome['prices'])} bookmaker(s) quoting, seen {best['observed_at']}"
            )


if __name__ == "__main__":
    main()

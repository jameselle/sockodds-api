#!/usr/bin/env python3
"""Compare one game's winner prices across every bookmaker and print the best price for each side.

    export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
    python3 odds_comparison.py [EVENT_ID]

With no EVENT_ID (or SOCKODDS_EVENT_ID) it uses the next game in SOCKODDS_LEAGUE (default nfl).
One request returns every bookmaker's quotes for the event, so there is no call per bookmaker.
Python 3.8+, standard library only. Mirrors https://sockodds.com/docs/examples/odds-comparison/
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


def next_event_id():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    events = get("/events", league=LEAGUE, starts_after=now, limit=1)["data"]
    if not events:
        sys.exit(f"No upcoming {LEAGUE} game. Pass an event id or set SOCKODDS_LEAGUE.")
    return events[0]["id"]


def main():
    if not KEY:
        sys.exit("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/")
    event_id = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SOCKODDS_EVENT_ID")) or next_event_id()

    event = get(f"/events/{event_id}/odds", markets="winner")["data"]
    # The full-game winner market. Each outcome lists every bookmaker's price, best first.
    market = next((m for m in event["markets"] if m["key"] == "winner" and m["period"] == "full"), None)
    outcomes = {outcome["side"]: outcome for outcome in (market["outcomes"] if market else [])}

    print(f"{event['name']}, winner (full game)")
    for participant in event["participants"]:
        outcome = outcomes.get(participant["role"])
        if outcome is None:
            print(f"  {participant['identity']['name']}: no current price")
            continue
        best = outcome["prices"][0]
        print(
            f"  {outcome['name']}: best {best['decimal_odds']:.2f} at {best['bookmaker']}, "
            f"seen {best['observed_at']}, {len(outcome['prices'])} bookmaker(s) quoting"
        )
        print("    all: " + ", ".join(f"{p['bookmaker']} {p['decimal_odds']:.2f}" for p in outcome["prices"]))


if __name__ == "__main__":
    main()

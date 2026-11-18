#!/usr/bin/env python3
"""Track line movement: how each bookmaker's winner price moved over a window, from recorded history.

    export SOCKODDS_API_KEY="your-key"     # paid plan (history): https://sockodds.com/pricing/
    python3 line_movement.py EVENT_ID [FROM TO]

FROM and TO are UTC times such as 2026-12-05T00:00:00Z; the default is the last 8 hours. A window
may be at most 24 hours. Rows have kind opened, changed or withdrawn (a withdrawal has no price).
Python 3.8+, standard library only. Mirrors https://sockodds.com/docs/examples/line-movement/
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("SOCKODDS_BASE_URL", "https://api.sockodds.com/v1").rstrip("/")
KEY = os.environ.get("SOCKODDS_API_KEY")


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
        if error.code == 403:
            message += " (recorded history is on every paid plan: https://sockodds.com/pricing/)"
        sys.exit(f"HTTP {error.code} from {url.split('?')[0]}: {message}")


def main():
    if not KEY:
        sys.exit("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/")
    event_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SOCKODDS_EVENT_ID")
    if not event_id:
        sys.exit("Usage: python3 line_movement.py EVENT_ID [FROM TO]")
    now = datetime.now(timezone.utc)
    window_from = sys.argv[2] if len(sys.argv) > 3 else (now - timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    window_to = sys.argv[3] if len(sys.argv) > 3 else now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # First and latest price per bookmaker, side and period. Rows arrive oldest first.
    moves = {}
    body = get("/odds/history", event_id=event_id, markets="winner", limit=250, **{"from": window_from, "to": window_to})
    while True:
        for row in body["data"]:
            if row["decimal_odds"] is None:
                continue  # a withdrawal has no price
            key = f"{row['bookmaker']}|{row['outcome']['side']}|{row['market']['period']}"
            move = moves.setdefault(key, {"bookmaker": row["bookmaker"], "name": row["outcome"]["name"],
                                          "first": row["decimal_odds"], "changes": 0})
            move["latest"] = row["decimal_odds"]
            move["at"] = row["observed_at"]
            move["changes"] += 1 if row["kind"] == "changed" else 0
        if not body["links"]["next"]:
            break
        body = get(body["links"]["next"])

    if not moves:
        print("No recorded winner prices in this window.")
    for key in sorted(moves):
        m = moves[key]
        diff = m["latest"] - m["first"]
        sign = "+" if diff > 0 else ""
        print(
            f"{m['bookmaker'].ljust(14)} {m['name'].ljust(14)} {m['first']:.2f} to {m['latest']:.2f} "
            f"({sign}{diff:.2f}), changes: {m['changes']}, latest {m['at']}"
        )


if __name__ == "__main__":
    main()

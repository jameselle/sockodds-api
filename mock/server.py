#!/usr/bin/env python3
"""A local mock of SockOdds API v1 that serves invented sample data.

    python3 mock/server.py               # http://127.0.0.1:8787/v1
    python3 mock/server.py --port 9000

Then point any example at it:

    export SOCKODDS_BASE_URL=http://127.0.0.1:8787/v1
    export SOCKODDS_API_KEY=sample-key-not-real
    export SOCKODDS_LEAGUE=sample_league

SAMPLE DATA ONLY. Every league, team, bookmaker, event, id and price below is
invented for testing. None of it is a real odd, a real event or a real
bookmaker. The real API is at https://api.sockodds.com/v1.

The mock follows the response shapes in openapi.json (tests/check_mock.py checks
every route against the contract) and covers the routes the examples use:
/sports, /leagues, /bookmakers, /markets, /events, /events/{id},
/events/{id}/odds, /odds, /odds/history and /results. It honours the `league`,
`event_id`, `markets` and `snapshots` filters and the bearer header, and it
uses small pages so pagination code paths run. Anything else returns a 404
problem. Standard library only.
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

LEAGUE = {"key": "sample_league", "name": "Sample League (demo data)"}
SPORT = {"key": "sample_sport", "name": "Sample sport", "participants": "teams"}
BOOKMAKERS = [
    {"key": "sample_book_a", "name": "Sample Book A", "regions": ["au"], "kind": "sportsbook"},
    {"key": "sample_book_b", "name": "Sample Book B", "regions": ["au"], "kind": "sportsbook"},
    {"key": "sample_book_c", "name": "Sample Book C", "regions": ["au", "us"], "kind": "sportsbook"},
]
MARKETS = [
    {"key": "winner", "name": "Winner", "subject": "event", "periods": ["full", "half_1"],
     "sports": ["sample_sport"], "sides": ["home", "away"]},
    {"key": "handicap", "name": "Line", "subject": "event", "periods": ["full"],
     "sports": ["sample_sport"], "sides": ["home", "away"]},
    {"key": "total_points", "name": "Total points", "subject": "event", "periods": ["full"],
     "sports": ["sample_sport"], "sides": ["over", "under"]},
]
SEEN = "2026-12-05T07:58:00.000Z"


def team(key, name):
    return {"key": key, "name": name}


def event(event_id, home, away, start, status="scheduled"):
    return {
        "id": event_id,
        "name": f"{home['name']} v {away['name']}",
        "league": dict(LEAGUE),
        "scheduled_start": start,
        "status": status,
        "participants": [{"role": "home", "identity": home}, {"role": "away", "identity": away}],
    }


HOME, AWAY = team("example_home", "Example Home"), team("example_away", "Example Away")
NORTH, SOUTH = team("example_north", "Example North"), team("example_south", "Example South")
EAST, WEST = team("example_east", "Example East"), team("example_west", "Example West")

EVENTS = {
    "ev_0000000000a1": event("ev_0000000000a1", HOME, AWAY, "2026-12-05T09:30:00.000Z"),
    "ev_0000000000a2": event("ev_0000000000a2", NORTH, SOUTH, "2026-12-06T04:00:00.000Z"),
    "ev_0000000000b1": event("ev_0000000000b1", EAST, WEST, "2026-11-28T09:30:00.000Z", status="final"),
}

# Sample prices: {event_id: [(market_id, key, name, period, [(outcome_id, name, side, line, {book: odds})])]}
PRICES = {
    "ev_0000000000a1": [
        ("mk_000000000000a1w1", "winner", "Winner", "full", [
            ("oc_000000000000a1h1", "Example Home", "home", None,
             {"sample_book_a": 1.87, "sample_book_b": 1.95, "sample_book_c": 1.85}),
            ("oc_000000000000a1a1", "Example Away", "away", None,
             {"sample_book_a": 1.98, "sample_book_b": 1.9, "sample_book_c": 2.04}),
        ]),
        ("mk_000000000000a1h2", "handicap", "Line", "full", [
            ("oc_000000000000a1h2", "Example Home", "home", -3.5, {"sample_book_a": 1.91, "sample_book_c": 1.95}),
            ("oc_000000000000a1a2", "Example Away", "away", 3.5, {"sample_book_a": 1.91, "sample_book_c": 1.88}),
        ]),
        ("mk_000000000000a1t3", "total_points", "Total points", "full", [
            ("oc_000000000000a1v3", "Over", "over", 45.5, {"sample_book_a": 1.9, "sample_book_b": 2.08}),
            ("oc_000000000000a1n3", "Under", "under", 45.5, {"sample_book_a": 1.95, "sample_book_c": 1.92}),
        ]),
    ],
    "ev_0000000000a2": [
        ("mk_000000000000a2w1", "winner", "Winner", "full", [
            ("oc_000000000000a2h1", "Example North", "home", None, {"sample_book_a": 1.62, "sample_book_b": 1.6}),
        ]),
    ],
}

# Sample opening prices for snapshots=opening (closing is the current price before the start).
OPENING = {"sample_book_a": 0.08, "sample_book_b": 0.07, "sample_book_c": 0.09}


def price(book, odds, snapshots):
    body = {
        "bookmaker": book,
        "decimal_odds": odds,
        "implied_probability": round(1 / odds, 6),
        "available": True,
        "observed_at": SEEN,
    }
    if "opening" in snapshots:
        opened = round(odds + OPENING[book], 2)
        body["opening"] = {"decimal_odds": opened, "implied_probability": round(1 / opened, 6),
                           "observed_at": "2026-12-04T22:05:00.000Z"}
    if "closing" in snapshots:
        body["closing"] = {"decimal_odds": odds, "implied_probability": round(1 / odds, 6), "observed_at": SEEN}
    return body


def odds_event(event_id, markets_filter, snapshots):
    body = dict(EVENTS[event_id])
    body["markets"] = []
    for market_id, key, name, period, outcomes in PRICES.get(event_id, []):
        if markets_filter and key not in markets_filter:
            continue
        priced = []
        for outcome_id, outcome_name, side, line, books in outcomes:
            prices = [price(book, odds, snapshots) for book, odds in books.items()]
            prices.sort(key=lambda p: (-p["decimal_odds"], p["bookmaker"]))
            priced.append({"id": outcome_id, "name": outcome_name, "side": side, "line": line, "prices": prices})
        body["markets"].append({"id": market_id, "key": key, "name": name, "period": period,
                                "subject": None, "alternate": False, "outcomes": priced})
    return body


def history_rows(event_id, markets_filter):
    """Sample recorded changes for the winner market: opened, then two changes per bookmaker and side."""
    rows = []
    if event_id != "ev_0000000000a1" or (markets_filter and "winner" not in markets_filter):
        return rows
    market_id, key, name, period, outcomes = PRICES[event_id][0]
    market = {"id": market_id, "key": key, "name": name, "period": period, "subject": None}
    times = ["2026-12-05T00:05:00.000Z", "2026-12-05T03:00:00.000Z", SEEN]
    for step, observed_at in enumerate(times):
        for outcome_id, outcome_name, side, line, books in outcomes:
            for book, odds in sorted(books.items()):
                drift = [0.08, 0.04, 0.0][step]  # home shortens into its current price, away drifts out
                value = round(odds + drift if side == "home" else odds - drift, 2)
                rows.append({
                    "event": event_id, "market": market,
                    "outcome": {"id": outcome_id, "name": outcome_name, "side": side},
                    "bookmaker": book, "observed_at": observed_at,
                    "kind": "opened" if step == 0 else "changed",
                    "decimal_odds": value, "implied_probability": round(1 / value, 6), "line": line,
                })
    # One withdrawal, which carries no price.
    rows.append({
        "event": event_id, "market": market,
        "outcome": {"id": "oc_000000000000a1a1", "name": "Example Away", "side": "away"},
        "bookmaker": "sample_book_c", "observed_at": "2026-12-05T05:10:00.000Z",
        "kind": "withdrawn", "decimal_odds": None, "implied_probability": None, "line": None,
    })
    rows.sort(key=lambda r: r["observed_at"])
    return rows


def result(event_id):
    if event_id != "ev_0000000000b1":
        return None

    def market(suffix, key, name, period):
        return {"id": f"mk_000000000000b1{suffix}", "key": key, "name": name, "period": period, "subject": None}

    winner, half, line = market("w1", "winner", "Winner", "full"), market("w2", "winner", "Winner", "half_1"), \
        market("h3", "handicap", "Line", "full")
    return {
        "event": dict(EVENTS[event_id]),
        "box_score": None,
        "status": "final",
        "settlement": "partial",
        "pending_markets": 1,
        "settled_at": "2026-11-28T13:02:00.000Z",
        "outcomes": [
            {"id": "oc_000000000000b1h1", "name": "Example East", "verdict": "won", "market": winner,
             "side": "home", "line": None},
            {"id": "oc_000000000000b1a1", "name": "Example West", "verdict": "lost", "market": winner,
             "side": "away", "line": None},
            {"id": "oc_000000000000b1h2", "name": "Example East", "verdict": "dead_heat", "dead_heat_factor": 0.5,
             "market": half, "side": "home", "line": None},
            {"id": "oc_000000000000b1a2", "name": "Example West", "verdict": "dead_heat", "dead_heat_factor": 0.5,
             "market": half, "side": "away", "line": None},
            {"id": "oc_000000000000b1h3", "name": "Example East", "verdict": "won", "market": line,
             "side": "home", "line": -3.5},
            {"id": "oc_000000000000b1a3", "name": "Example West", "verdict": "lost", "market": line,
             "side": "away", "line": 3.5},
        ],
    }


def problem(status, title, detail, instance):
    return status, {"type": f"https://api.sockodds.com/problems/{status}", "title": title, "status": status,
                    "detail": detail, "instance": instance}


class Handler(BaseHTTPRequestHandler):
    server_version = "sockodds-mock/1.0"

    def log_message(self, fmt, *args):  # keep test output quiet
        if self.server.verbose:
            sys.stderr.write("mock: " + fmt % args + "\n")

    def do_GET(self):
        url = urlsplit(self.path)
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}
        status, body = self.route(url.path, query)
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json" if status < 400 else "application/problem+json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def page(self, path, query, items, size):
        """Pages a list by an integer cursor, `size` items a page at most."""
        size = min(size, int(query.get("limit", size)))
        start = int(query.get("cursor", "0") or 0)
        chunk = items[start:start + size]
        cursor = str(start + size) if start + size < len(items) else None
        nxt = None
        if cursor:
            nxt = f"http://{self.headers.get('Host')}{path}?" + urlencode({**query, "cursor": cursor})
        return 200, {"data": chunk, "meta": {"count": len(chunk), "cursor": cursor}, "links": {"next": nxt}}

    def route(self, path, query):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not auth[7:].strip():
            return problem(401, "Unauthorised", "Provide a valid bearer key.", path)
        if not path.startswith("/v1/"):
            return problem(404, "Not found", "No such route.", path)
        parts = path[4:].strip("/").split("/")
        league_ok = query.get("league") in (None, LEAGUE["key"])
        markets = set(filter(None, query.get("markets", "").split(",")))
        snapshots = set(filter(None, query.get("snapshots", "").split(",")))

        if parts == ["sports"]:
            return self.page(path, query, [SPORT], 100)
        if parts == ["leagues"]:
            return self.page(path, query, [{**LEAGUE, "sport": SPORT["key"], "region": "au"}], 100)
        if parts == ["bookmakers"]:
            return self.page(path, query, BOOKMAKERS, 100)
        if parts == ["markets"]:
            return self.page(path, query, MARKETS if league_ok else [], 100)
        if parts == ["events"]:
            items = [EVENTS["ev_0000000000a1"], EVENTS["ev_0000000000a2"]] if league_ok else []
            return self.page(path, query, items, 100)
        if len(parts) >= 2 and parts[0] == "events" and parts[1] in EVENTS:
            if len(parts) == 2:
                return 200, {"data": EVENTS[parts[1]], "meta": {"count": 1, "cursor": None}, "links": {"next": None}}
            if parts[2:] == ["odds"]:
                return 200, {"data": odds_event(parts[1], markets, snapshots),
                             "meta": {"count": 1, "cursor": None}, "links": {"next": None}}
        if len(parts) >= 2 and parts[0] == "events":
            return problem(404, "Not found", "No event has this id.", path)
        if parts == ["odds"]:
            items = [odds_event(e, markets, set()) for e in ("ev_0000000000a1", "ev_0000000000a2")] if league_ok else []
            return self.page(path, query, items, 1)
        if parts == ["odds", "history"]:
            missing = [name for name in ("event_id", "from", "to") if not query.get(name)]
            if missing:
                return problem(400, "Bad request", "Missing required parameter: " + ", ".join(missing) + ".", path)
            return self.page(path, query, history_rows(query["event_id"], markets), 8)
        if parts == ["results"]:
            found = result(query.get("event_id", "ev_0000000000b1"))
            return self.page(path, query, [found] if found and league_ok else [], 100)
        return problem(404, "Not found", "The mock does not serve this route.", path)


def main():
    parser = argparse.ArgumentParser(description="Local mock of SockOdds API v1 (sample data only).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.verbose = args.verbose
    print(f"SockOdds mock (sample data) on http://{args.host}:{server.server_address[1]}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

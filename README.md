# SockOdds API

The OpenAPI contract, a Postman collection and runnable examples for [SockOdds](https://sockodds.com/), a sports odds API for Australian and global sport.

[![OpenAPI 3.1](https://img.shields.io/badge/OpenAPI-3.1-6BA539)](openapi.json)
[![Postman collection](https://img.shields.io/badge/Postman-collection-FF6C37)](sockodds-api-v1.postman_collection.json)
[![MCP server](https://img.shields.io/badge/MCP-sockodds--mcp-5A45FF)](https://github.com/jameselle/sockodds-mcp)
[![Licence: MIT (spec and examples)](https://img.shields.io/badge/licence-MIT%20(spec%20%26%20examples)-blue)](LICENSE)

One REST API returns bookmaker prices that SockOdds records itself, with readable keys, stable ids, recorded price history and results graded from official sources. This repository is the public developer kit for it. The API itself lives at `https://api.sockodds.com/v1` and the full documentation at [sockodds.com/docs](https://sockodds.com/docs/).

- [What you get](#what-you-get)
- [Coverage](#coverage)
- [Quick start](#quick-start)
- [Try it with no key](#try-it-with-no-key)
- [Examples](#examples)
- [Postman](#postman)
- [OpenAPI contract](#openapi-contract)
- [AI assistants and the MCP server](#ai-assistants-and-the-mcp-server)
- [Plans and pricing](#plans-and-pricing)
- [Support](#support)
- [Licence](#licence)

## What you get

- **Every bookmaker in one shape.** Sportsbooks, betting exchanges and prediction markets come back in the same response, as decimal odds. Each market appears once, and each outcome lists every bookmaker's price, best first, so `prices[0]` is the best price.
- **A time on every price.** Each price carries `observed_at`, the moment SockOdds saw it. A quote not seen for ten minutes is withheld from current responses rather than shown as current.
- **Readable keys and stable ids.** Sports, leagues, bookmakers, markets, periods and sides have readable keys (`nfl`, `winner`, `home`, `over`). Events, players, markets and outcomes have ids (`ev_`, `pl_`, `mk_`, `oc_`) that stay the same across prices, history and results.
- **Recorded price history.** Every recorded price change for an event, opening and closing prices, and whole days of history as Parquet files, on paid plans. See [history](https://sockodds.com/docs/history/).
- **Results graded from official sources.** Each outcome gets a verdict: `won`, `lost`, `void`, `dead_heat` (with its factor) or, on Asian quarter lines, `half_won` and `half_lost`. Outcomes that official evidence cannot settle are left out, never guessed. See [results](https://sockodds.com/docs/results/).
- **Player market rules.** Player prices say how that bookmaker settles a player who takes no part (`void`, `loses`, `under` or `fair_price`), so you can filter to the ones you want.
- **A WebSocket stream** of current prices for an event or a league, on paid plans. See [streaming](https://sockodds.com/docs/streaming/).
- **Australian and New Zealand racing**: race cards, win and place prices by bookmaker, exchange back and lay, and price movement. See [racing](https://sockodds.com/docs/racing/).
- **Plain HTTP that is easy to build on.** Bearer key auth, `{data, meta, links}` envelopes, cursor pagination through `links.next`, and errors as `application/problem+json`.

## Coverage

SockOdds started with Australian sport and Australian bookmakers, and now also carries US sportsbooks, betting exchanges and prediction markets. Sports include Australian football, rugby league, basketball, American football, baseball, ice hockey, soccer, tennis and mixed martial arts, plus Australian and New Zealand thoroughbred, harness and greyhound racing.

Some honest limits:

- **Coverage changes week to week.** Leagues go in and out of season, and the number of bookmakers pricing a league varies a lot: some leagues are priced by many bookmakers, others by one or two. The live lists are the source of truth: [leagues](https://sockodds.com/leagues/), [bookmakers](https://sockodds.com/bookmakers/) and [markets](https://sockodds.com/docs/markets/).
- **Your plan decides what your key sees.** Prices from bookmakers or leagues outside your plan are left out of responses rather than refused.
- **Pre-match first.** Event status and the latest prices are available while games are live, polled or streamed, but SockOdds is not a low-latency in-play trading feed.
- **History has a start date.** Recorded history goes back to late December 2025 for some leagues and October 2026 for the rest; see [how far back it goes](https://sockodds.com/docs/history/).
- **A best price is a quote, not an offer.** Bookmakers change prices often and may limit or refuse a bet. Always check the price at the bookmaker.

## Quick start

1. Get a free key at [sockodds.com/signup](https://sockodds.com/signup/). No card is needed.
2. Keep it in an environment variable, never in code or a URL:

   ```bash
   export SOCKODDS_API_KEY="paste-your-key-here"
   ```

3. List the sports your key can read:

   ```bash
   curl -sS "https://api.sockodds.com/v1/sports" \
     -H "Authorization: Bearer $SOCKODDS_API_KEY"
   ```

4. Ask for prices: the winner market for the next NFL game, from every bookmaker your plan includes:

   ```bash
   curl -sS "https://api.sockodds.com/v1/odds?league=nfl&markets=winner&limit=1&starts_after=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     -H "Authorization: Bearer $SOCKODDS_API_KEY"
   ```

A response looks like this (sample data, not real odds, trimmed to one outcome):

```json
{
  "data": [
    {
      "id": "ev_0000000000a1",
      "name": "Example Home v Example Away",
      "league": { "key": "sample_league", "name": "Sample League (demo data)" },
      "scheduled_start": "2026-12-05T09:30:00.000Z",
      "status": "scheduled",
      "participants": [
        { "role": "home", "identity": { "key": "example_home", "name": "Example Home" } },
        { "role": "away", "identity": { "key": "example_away", "name": "Example Away" } }
      ],
      "markets": [
        {
          "id": "mk_000000000000a1w1",
          "key": "winner",
          "name": "Winner",
          "period": "full",
          "subject": null,
          "alternate": false,
          "outcomes": [
            {
              "id": "oc_000000000000a1h1",
              "name": "Example Home",
              "side": "home",
              "line": null,
              "prices": [
                { "bookmaker": "sample_book_b", "decimal_odds": 1.95, "implied_probability": 0.512821, "available": true, "observed_at": "2026-12-05T07:58:00.000Z" },
                { "bookmaker": "sample_book_a", "decimal_odds": 1.87, "implied_probability": 0.534759, "available": true, "observed_at": "2026-12-05T07:58:00.000Z" }
              ]
            }
          ]
        }
      ]
    }
  ],
  "meta": { "count": 1, "cursor": "sample-cursor" },
  "links": { "next": "https://api.sockodds.com/v1/odds?league=nfl&markets=winner&limit=1&cursor=sample-cursor" }
}
```

The [quickstart](https://sockodds.com/docs/quickstart/) walks through every field.

## Try it with no key

`mock/server.py` is a small local copy of the API that serves invented sample data in the same shapes as the real thing (checked against `openapi.json` by `tests/check_mock.py`). It needs only Python 3.8+:

```bash
python3 mock/server.py &                       # http://127.0.0.1:8787/v1
export SOCKODDS_BASE_URL=http://127.0.0.1:8787/v1
export SOCKODDS_API_KEY=sample-key-not-real    # the mock accepts any key
export SOCKODDS_LEAGUE=sample_league
python3 examples/python/odds_comparison.py
```

Every league, team, bookmaker, id and price in the mock is made up. Unset `SOCKODDS_BASE_URL` to go back to the real API.

## Examples

Each example comes in curl (with `jq`), Python (standard library only) and JavaScript (Node 18+, no dependencies). They read your key from `SOCKODDS_API_KEY` and mirror the [examples on the docs site](https://sockodds.com/docs/examples/odds-comparison/).

| Example | What it does | curl | Python | JavaScript |
| --- | --- | --- | --- | --- |
| First request | The sports your key can read, then the next game's winner prices | [sh](examples/curl/first-request.sh) | [py](examples/python/first_request.py) | [mjs](examples/javascript/first-request.mjs) |
| Odds comparison | Best price for each side of one game, across every bookmaker, in one request | [sh](examples/curl/odds-comparison.sh) | [py](examples/python/odds_comparison.py) | [mjs](examples/javascript/odds-comparison.mjs) |
| Arbitrage check | The combined margin of each market at the best prices, following pagination | [sh](examples/curl/arbitrage.sh) | [py](examples/python/arbitrage.py) | [mjs](examples/javascript/arbitrage.mjs) |
| Line movement | How each bookmaker's price moved over a window, from recorded history (paid plans) | [sh](examples/curl/line-movement.sh) | [py](examples/python/line_movement.py) | [mjs](examples/javascript/line-movement.mjs) |
| Settle bets | Each bet's verdict and return from graded results, including dead heats and pending markets | [sh](examples/curl/settle-bets.sh) | [py](examples/python/settle_bets.py) | [mjs](examples/javascript/settle-bets.mjs) |

See [examples/README.md](examples/README.md) for arguments and sample output.

## Postman

[`sockodds-api-v1.postman_collection.json`](sockodds-api-v1.postman_collection.json) has one request for every HTTP operation, in folders by tag (Catalogue, Identity, Prices, Results, History, Racing). It is generated from `openapi.json` by [`scripts/generate_postman.py`](scripts/generate_postman.py).

1. In Postman choose **Import** and drop in the file (or paste `https://sockodds.com/postman.json`).
2. Open the collection's **Variables** tab. `baseUrl` is filled in. Put your key in `sockoddsKey` as the **current value** only, so it is never shared or exported.
3. Send `listSports`, then `listEvents` to copy an event id, then `getEventOdds` with that id.

Ids and dates in the example values are placeholders. The odds stream is a WebSocket, so it is not in the collection.

## OpenAPI contract

[`openapi.json`](openapi.json) is the OpenAPI 3.1 contract published at [sockodds.com/openapi.json](https://sockodds.com/openapi.json). Use it to generate a client, load it into your API tool, or give it to an AI assistant. For example, with [OpenAPI Generator](https://openapi-generator.tech/):

```bash
npx @openapitools/openapi-generator-cli generate -i openapi.json -g python -o sockodds-client
```

Refresh it from the live contract and regenerate the Postman collection with:

```bash
python3 scripts/refresh_openapi.py
python3 scripts/generate_postman.py
```

The refresh script tidies two things in the published file: a few descriptions that had a comma split off into a stray key are rejoined, and access notes name only the plans you can buy. It changes nothing else.

## AI assistants and the MCP server

- **MCP server:** [`sockodds-mcp`](https://github.com/jameselle/sockodds-mcp) (npm [`sockodds-mcp`](https://www.npmjs.com/package/sockodds-mcp)) lets Claude and other MCP clients find events, compare prices and work out the no-vig fair price. Try it on sample data with no key:

  ```bash
  claude mcp add sockodds --env SOCKODDS_DEMO=1 -- npx -y sockodds-mcp
  ```

- **Docs for models:** [llms.txt](https://sockodds.com/llms.txt), an [AI starter context](https://sockodds.com/ai-context.md) and a Markdown copy of every docs page. See [building with AI](https://sockodds.com/docs/ai-tools/). Keep your key out of the chat.

## Plans and pricing

There is a free key for building and testing, and paid plans add bookmakers, leagues, recorded history and streaming. Plans, limits and how usage is metered change from time to time, so this README does not repeat them: see [pricing](https://sockodds.com/pricing/) and [plans and limits](https://sockodds.com/docs/limits/), and re-run `scripts/refresh_openapi.py` to pick up contract changes.

## Develop

Everything runs locally; there is no CI.

```bash
tests/run_examples.sh                 # runs all 15 examples against the mock and checks their output
pip install "jsonschema>=4.18" && python3 tests/check_mock.py   # checks the mock against openapi.json
python3 scripts/generate_postman.py --check
python3 scripts/refresh_openapi.py --check
```

```text
openapi.json                              OpenAPI 3.1 contract (from sockodds.com/openapi.json)
sockodds-api-v1.postman_collection.json   Postman collection generated from the contract
scripts/refresh_openapi.py                refreshes openapi.json from the live contract
scripts/generate_postman.py               generates the Postman collection
examples/                                 curl, Python and JavaScript examples
mock/server.py                            local mock API with invented sample data
tests/                                    example and mock checks
rapidapi-listing.md                       draft marketplace listing copy
```

## Support

Email [support@sockodds.com](mailto:support@sockodds.com). Found a problem with the spec, the collection or an example? Open an issue on this repository.

## Licence

The contents of this repository (the spec, the Postman collection, the scripts, the examples and the mock data) are [MIT licensed](LICENSE). Data served by the SockOdds API is not: it is licensed under the [SockOdds Terms of Service](https://sockodds.com/terms/), which restrict resale and redistribution. Bookmaker names and marks belong to their owners.

SockOdds is a data service, not a bookmaker: it does not take bets or give betting advice. If you build a product that shows odds, you are responsible for age gating and the responsible gambling and advertising rules where your users are. 18+.

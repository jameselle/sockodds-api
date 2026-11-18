# RapidAPI listing (draft)

Draft copy for a SockOdds listing on the RapidAPI Hub. **Nothing has been listed.** Creating the provider account, connecting the API and setting plans needs the SockOdds owner; see [Before publishing](#before-publishing).

Plan prices, quotas and bookmaker or league counts are deliberately left out: they change, so the listing links to the live pages instead of repeating them.

---

## Name

SockOdds: Sports Odds API (Australia and global)

## Tagline (short description)

Bookmaker, exchange and prediction market odds in one shape, with recorded price history and results graded from official sources. Australian sport first: AFL, NRL, NBL and racing, plus NFL, NBA, soccer and more.

## Category

Sports (secondary: Data)

## Tags

odds, sports odds, betting odds, sportsbook, odds comparison, line movement, historical odds, closing line, results, bet settlement, arbitrage, positive ev, afl, nrl, nfl, nba, epl, horse racing, australia, prediction markets

## Long description

```markdown
# SockOdds Sports Odds API

One REST API for bookmaker prices that SockOdds records itself, across Australian and global
sportsbooks, betting exchanges and prediction markets, all as decimal odds in one response shape.

## Why developers pick it

- **Every bookmaker in one request.** Each market appears once; each outcome lists every
  bookmaker's price, best first, so `prices[0]` is the best price.
- **A time on every price.** Each quote carries `observed_at`. Quotes not seen for ten minutes
  are withheld from current responses instead of being shown as current.
- **Stable ids across everything.** Events, markets and outcomes keep the same `ev_`, `mk_` and
  `oc_` ids in prices, history and results, so storing a bet and settling it later is a join.
- **Recorded history.** Every recorded price change, opening and closing prices, and whole days
  as Parquet files (higher plans).
- **Graded results.** Verdicts per outcome: won, lost, void, dead heat (with its factor),
  half won and half lost, from official sources only. Nothing is guessed.
- **Australian and New Zealand racing.** Race cards, win and place prices by bookmaker,
  exchange back and lay, and price movement.
- **Built for code and AI.** OpenAPI 3.1 contract, Postman collection, llms.txt, Markdown docs
  and an MCP server.

## Coverage

Australian football, rugby league, basketball, American football, baseball, ice hockey,
soccer, tennis and MMA, plus thoroughbred, harness and greyhound racing. Coverage moves with
the seasons; the live league and bookmaker lists are at https://sockodds.com/leagues/ and
https://sockodds.com/bookmakers/.

## Endpoints

Catalogue: /sports, /leagues, /bookmakers, /markets
Identity: /teams, /players, /events, /events/lookup, /events/{event_id}
Prices: /odds, /events/{event_id}/odds, /odds/history, /stream/odds (WebSocket)
History: /history/files, /history/files/{league}/{day}
Results: /results
Racing: /racing/races, /racing/races/{race_id}, /racing/races/{race_id}/odds,
        /racing/races/{race_id}/history

## Good fits

Odds comparison sites, alert bots, betting models and backtests, bet trackers and settlement,
positive EV and arbitrage tools, AI agents.

## Not a fit

SockOdds does not take bets and is not a low-latency in-play trading feed. A best price is a
quote, not an offer: bookmakers change prices and may limit bets.

Docs: https://sockodds.com/docs/
Support: support@sockodds.com
```

## Example request (for the listing's code snippets)

```bash
curl -sS "https://api.sockodds.com/v1/odds?league=nfl&markets=winner&limit=1" \
  -H "Authorization: Bearer $SOCKODDS_API_KEY"
```

## Example response (sample data, not real odds)

```json
{
  "data": [
    {
      "id": "ev_0000000000a1",
      "name": "Example Home v Example Away",
      "league": { "key": "sample_league", "name": "Sample League (demo data)" },
      "scheduled_start": "2026-12-05T09:30:00.000Z",
      "status": "scheduled",
      "markets": [
        {
          "key": "winner",
          "period": "full",
          "outcomes": [
            {
              "name": "Example Home",
              "side": "home",
              "prices": [
                { "bookmaker": "sample_book_b", "decimal_odds": 1.95, "observed_at": "2026-12-05T07:58:00.000Z" },
                { "bookmaker": "sample_book_a", "decimal_odds": 1.87, "observed_at": "2026-12-05T07:58:00.000Z" }
              ]
            }
          ]
        }
      ]
    }
  ],
  "meta": { "count": 1, "cursor": null },
  "links": { "next": null }
}
```

(Trimmed for the listing. The full shape is in [openapi.json](openapi.json).)

## Plans

Link to https://sockodds.com/pricing/ rather than copying numbers. If RapidAPI plans are offered, map each one to an existing SockOdds plan so the limits match; do not invent RapidAPI-only limits.

## FAQ (listing tab)

**What odds format?** Decimal odds, exactly as the bookmaker showed them, plus `implied_probability` (1 / odds, margin included).

**How fresh are prices?** Every price carries `observed_at`. Anything not seen for ten minutes is withheld from current responses.

**Do you have historical odds?** Yes, on higher plans: recorded changes, opening and closing prices, and daily Parquet files. See https://sockodds.com/docs/history/.

**Can I settle bets with it?** Yes. `/results` grades each outcome from official sources with the same outcome ids the prices use.

**Is there a free tier?** Yes, a free Developer key at https://sockodds.com/signup/.

---

## Before publishing

Things only the owner can do or decide:

1. Create (or sign in to) the RapidAPI provider account and accept its provider terms.
2. Decide whether RapidAPI keys map to SockOdds keys. RapidAPI sends its own `X-RapidAPI-Key` and a proxy secret; the SockOdds API expects `Authorization: Bearer`. That needs either a header transform in the RapidAPI gateway with one SockOdds key per RapidAPI plan, or API-side support for the RapidAPI proxy secret. Neither exists yet.
3. Pick the plans to offer and their limits, from the live pricing page on the day of listing.
4. Import `openapi.json` as the API definition (RapidAPI accepts OpenAPI 3) and check the WebSocket stream route, which RapidAPI's REST proxy will not carry.
5. Add the logo, the terms link (https://sockodds.com/terms/) and support@sockodds.com as the support contact.
6. Read the final copy against the current pricing, leagues and bookmakers pages before going live.

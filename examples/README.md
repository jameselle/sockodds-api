# Examples

Five programs, each in curl (with `jq`), Python 3.8+ (standard library only) and JavaScript (Node 18+, no dependencies). They mirror the [examples on the SockOdds docs site](https://sockodds.com/docs/examples/odds-comparison/).

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `SOCKODDS_API_KEY` | none | Your key, sent only as `Authorization: Bearer`. [Get a free key](https://sockodds.com/signup/). |
| `SOCKODDS_LEAGUE` | `nfl` | League key for the examples that read a league. See [leagues](https://sockodds.com/leagues/). |
| `SOCKODDS_EVENT_ID` | none | Event id (`ev_...`) when no argument is given. |
| `SOCKODDS_BASE_URL` | `https://api.sockodds.com/v1` | Point it at the local mock to run with no key. |

## Run them

```bash
export SOCKODDS_API_KEY="your-key"

# First request
./curl/first-request.sh
python3 python/first_request.py
node javascript/first-request.mjs

# Odds comparison: one game (an event id, or the next game in SOCKODDS_LEAGUE)
python3 python/odds_comparison.py [EVENT_ID]

# Arbitrage check across every upcoming game in SOCKODDS_LEAGUE
python3 python/arbitrage.py

# Line movement from recorded history (paid plans): last 8 hours, or a window of up to 24 hours
python3 python/line_movement.py EVENT_ID [FROM TO]

# Settle sample bets against an event's graded results
python3 python/settle_bets.py EVENT_ID
```

The curl and JavaScript versions take the same arguments. Get an event id from `/v1/events` (or the first example's output).

## Run them with no key

```bash
python3 ../mock/server.py &
export SOCKODDS_BASE_URL=http://127.0.0.1:8787/v1 SOCKODDS_API_KEY=sample-key-not-real SOCKODDS_LEAGUE=sample_league
python3 python/odds_comparison.py ev_0000000000a1
python3 python/line_movement.py ev_0000000000a1
python3 python/settle_bets.py ev_0000000000b1
```

The mock serves invented sample data only. `../tests/run_examples.sh` runs all fifteen programs this way and checks their output.

## Sample output

All output below comes from the local mock. Every team, bookmaker, id and price is invented sample data, not real odds.

### Odds comparison

```text
Example Home v Example Away, winner (full game)
  Example Home: best 1.95 at sample_book_b, seen 2026-12-05T07:58:00.000Z, 3 bookmaker(s) quoting
    all: sample_book_b 1.95, sample_book_a 1.87, sample_book_c 1.85
  Example Away: best 2.04 at sample_book_c, seen 2026-12-05T07:58:00.000Z, 3 bookmaker(s) quoting
    all: sample_book_c 2.04, sample_book_a 1.98, sample_book_b 1.90
```

### Arbitrage check

```text
Example Home v Example Away
  Winner (full)
    home: 1.95 at sample_book_b
    away: 2.04 at sample_book_c
    sum 1.0030, margin 0.30%, over 1: no arbitrage
  Line -3.5 (full)
    home: 1.95 at sample_book_c
    away: 1.91 at sample_book_a
    sum 1.0364, margin 3.64%, over 1: no arbitrage
  Total points 45.5 (full)
    over: 2.08 at sample_book_b
    under: 1.95 at sample_book_a
    sum 0.9936, margin -0.64%, under 1: check every price is still up
Example North v Example South
  Winner (full): skipped, not every side has a current price
```

### Line movement

```text
sample_book_a  Example Away   1.90 to 1.98 (+0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
sample_book_a  Example Home   1.95 to 1.87 (-0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
sample_book_b  Example Away   1.82 to 1.90 (+0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
sample_book_b  Example Home   2.03 to 1.95 (-0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
sample_book_c  Example Away   1.96 to 2.04 (+0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
sample_book_c  Example Home   1.93 to 1.85 (-0.08), changes: 2, latest 2026-12-05T07:58:00.000Z
```

### Settle bets

```text
Example East v Example West: final, partial, markets pending: 1
  winner (full) home at 1.85: won, stake 10.00, returns 18.50, profit 8.50
  winner (half_1) home at 2.10: dead_heat, stake 10.00, returns 10.50, profit 0.50
  handicap (full) away 3.5 at 1.90: lost, stake 20.00, returns 0.00, profit -20.00
  total_points (full) over 45.5 at 1.87: pending, stake 10.00 still open
```

In the arbitrage output, the total points market sums to under 1 because the sample data was made that way to show the message. With real prices a sum under 1 is rare and short lived, a price can be gone by the time you act, and bookmakers may limit accounts that bet this way.

In the settle bets output, the total points bet stays pending: that market has no graded outcome yet, so the program leaves the stake open instead of calling it lost.

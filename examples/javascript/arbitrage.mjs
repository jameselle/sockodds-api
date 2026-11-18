// Check the market margin at the best prices: sum 1/price over the best price on every side.
//
//   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
//   node arbitrage.mjs
//
// Reads every upcoming game in SOCKODDS_LEAGUE (default nfl), following links.next. A sum under 1
// means the best prices carried no margin at the moment they were seen. With real prices that is
// rare and short lived, prices move, and bookmakers may limit accounts: treat this as a measure of
// how tight a market is, not a source of profit.
// Node 18+, no dependencies. Mirrors https://sockodds.com/docs/examples/arbitrage/

const BASE = (process.env.SOCKODDS_BASE_URL ?? "https://api.sockodds.com/v1").replace(/\/$/, "");
const KEY = process.env.SOCKODDS_API_KEY;
const LEAGUE = process.env.SOCKODDS_LEAGUE ?? "nfl";

// GET a SockOdds route (or a full links.next URL) and return the JSON body.
async function get(path, params = {}) {
  let url = path.startsWith("http") ? path : BASE + path;
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;
  const response = await fetch(url, { headers: { Authorization: `Bearer ${KEY}`, Accept: "application/json" } });
  if (!response.ok) {
    // errors are application/problem+json
    const problem = await response.json().catch(() => ({}));
    console.error(`HTTP ${response.status} from ${url.split("?")[0]}: ${problem.title ?? response.statusText}: ${problem.detail ?? ""}`);
    process.exit(1);
  }
  return response.json();
}

// Every item of a list route: follow links.next unchanged until it is null.
async function getAll(path, params) {
  let body = await get(path, params);
  const rows = [...body.data];
  while (body.links.next) {
    body = await get(body.links.next);
    rows.push(...body.data);
  }
  return rows;
}

if (!KEY) {
  console.error("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/");
  process.exit(1);
}

// Which sides make up each market in this league (from the catalogue; cache this in your code).
const sides = new Map();
for (const market of await getAll("/markets", { league: LEAGUE, limit: 100 })) {
  if (Array.isArray(market.sides)) sides.set(market.key, market.sides);
}

const now = new Date().toISOString().slice(0, 19) + "Z";
for (const event of await getAll("/odds", { league: LEAGUE, limit: 25, starts_after: now })) {
  console.log(event.name);
  for (const market of event.markets) {
    const outcomes = new Map(market.outcomes.map((outcome) => [outcome.side, outcome]));
    const keys = sides.get(market.key);
    if (!keys || !keys.every((side) => outcomes.get(side)?.prices.length)) {
      console.log(`  ${market.name} (${market.period}): skipped, not every side has a current price`);
      continue;
    }
    const first = outcomes.get(keys[0]);
    const label = market.name + (first.line === null ? "" : ` ${first.line}`) + ` (${market.period})`;
    const sum = keys.reduce((total, side) => total + 1 / outcomes.get(side).prices[0].decimal_odds, 0);
    console.log(`  ${label}`);
    for (const side of keys) {
      const best = outcomes.get(side).prices[0]; // prices are sorted best first
      console.log(`    ${side}: ${best.decimal_odds.toFixed(2)} at ${best.bookmaker}`);
    }
    const note = sum < 1 ? "under 1: check every price is still up" : "over 1: no arbitrage";
    console.log(`    sum ${sum.toFixed(4)}, margin ${((sum - 1) * 100).toFixed(2)}%, ${note}`);
  }
}

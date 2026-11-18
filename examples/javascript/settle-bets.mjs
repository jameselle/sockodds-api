// Settle bets from graded results: each bet's verdict and return, including dead heats and pending markets.
//
//   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
//   node settle-bets.mjs EVENT_ID
//
// The bets below are SAMPLE bets. In your code they come from your own database, stored with the
// event id (and ideally the outcome id) when each bet was placed. An outcome with no verdict yet is
// pending, never lost. Node 18+, no dependencies.
// Mirrors https://sockodds.com/docs/examples/settle-bets/

const BASE = (process.env.SOCKODDS_BASE_URL ?? "https://api.sockodds.com/v1").replace(/\/$/, "");
const KEY = process.env.SOCKODDS_API_KEY;

// Sample bets (invented stakes and prices).
const BETS = [
  { market: "winner", period: "full", side: "home", line: null, stake: 10, price: 1.85 },
  { market: "winner", period: "half_1", side: "home", line: null, stake: 10, price: 2.1 },
  { market: "handicap", period: "full", side: "away", line: 3.5, stake: 20, price: 1.9 },
  { market: "total_points", period: "full", side: "over", line: 45.5, stake: 10, price: 1.87 },
];

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

function returned(bet, outcome) {
  const { stake, price } = bet;
  switch (outcome.verdict) {
    case "won":
      return stake * price;
    case "void":
      return stake;
    case "dead_heat": // paid at dead_heat_factor of the stake, the rest lost
      return stake * outcome.dead_heat_factor * price;
    case "half_won": // Asian quarter line: half won at the price, half refunded
      return (stake / 2) * price + stake / 2;
    case "half_lost": // half refunded, half lost
      return stake / 2;
    default: // lost
      return 0;
  }
}

if (!KEY) {
  console.error("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/");
  process.exit(1);
}
const eventId = process.argv[2] || process.env.SOCKODDS_EVENT_ID;
if (!eventId) {
  console.error("Usage: node settle-bets.mjs EVENT_ID");
  process.exit(1);
}

const results = (await get("/results", { event_id: eventId })).data;
// One result per event. It gains outcomes as more markets settle, so read it again later.
const graded = results.flatMap((result) => result.outcomes);
if (results.length) {
  const last = results[results.length - 1];
  console.log(`${last.event.name}: ${last.status}, ${last.settlement}, markets pending: ${last.pending_markets}`);
} else {
  console.log(`${eventId}: no graded results yet`);
}

for (const bet of BETS) {
  const line = bet.line === null ? "" : ` ${bet.line}`;
  const label = `${bet.market} (${bet.period}) ${bet.side}${line} at ${bet.price.toFixed(2)}`;
  const outcome = graded.find(
    (o) => o.market.key === bet.market && o.market.period === bet.period && o.side === bet.side && o.line === bet.line,
  );
  if (!outcome) {
    console.log(`  ${label}: pending, stake ${bet.stake.toFixed(2)} still open`);
    continue;
  }
  const back = returned(bet, outcome);
  console.log(
    `  ${label}: ${outcome.verdict}, stake ${bet.stake.toFixed(2)}, returns ${back.toFixed(2)}, profit ${(back - bet.stake).toFixed(2)}`,
  );
}

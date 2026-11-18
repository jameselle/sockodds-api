// Compare one game's winner prices across every bookmaker and print the best price for each side.
//
//   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
//   node odds-comparison.mjs [EVENT_ID]
//
// With no EVENT_ID (or SOCKODDS_EVENT_ID) it uses the next game in SOCKODDS_LEAGUE (default nfl).
// One request returns every bookmaker's quotes for the event, so there is no call per bookmaker.
// Node 18+, no dependencies. Mirrors https://sockodds.com/docs/examples/odds-comparison/

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

async function nextEventId() {
  const now = new Date().toISOString().slice(0, 19) + "Z";
  const events = (await get("/events", { league: LEAGUE, starts_after: now, limit: 1 })).data;
  if (!events.length) {
    console.error(`No upcoming ${LEAGUE} game. Pass an event id or set SOCKODDS_LEAGUE.`);
    process.exit(1);
  }
  return events[0].id;
}

if (!KEY) {
  console.error("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/");
  process.exit(1);
}
const eventId = process.argv[2] || process.env.SOCKODDS_EVENT_ID || (await nextEventId());

const { data: event } = await get(`/events/${eventId}/odds`, { markets: "winner" });
// The full-game winner market. Each outcome lists every bookmaker's price, best first.
const market = event.markets.find((m) => m.key === "winner" && m.period === "full");
const outcomes = new Map((market?.outcomes ?? []).map((outcome) => [outcome.side, outcome]));

console.log(`${event.name}, winner (full game)`);
for (const participant of event.participants) {
  const outcome = outcomes.get(participant.role);
  if (!outcome) {
    console.log(`  ${participant.identity.name}: no current price`);
    continue;
  }
  const best = outcome.prices[0];
  console.log(
    `  ${outcome.name}: best ${best.decimal_odds.toFixed(2)} at ${best.bookmaker}, ` +
      `seen ${best.observed_at}, ${outcome.prices.length} bookmaker(s) quoting`,
  );
  console.log("    all: " + outcome.prices.map((p) => `${p.bookmaker} ${p.decimal_odds.toFixed(2)}`).join(", "));
}

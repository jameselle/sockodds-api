// Your first SockOdds requests: the sports your key can read, then the next game's winner prices.
//
//   export SOCKODDS_API_KEY="your-key"     # free key: https://sockodds.com/signup/
//   node first-request.mjs
//
// Optional: SOCKODDS_LEAGUE (default nfl), SOCKODDS_BASE_URL (default https://api.sockodds.com/v1).
// Node 18+, no dependencies.

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

if (!KEY) {
  console.error("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/");
  process.exit(1);
}

console.log("Sports your key can read:");
for (const sport of (await get("/sports")).data) {
  console.log(`  ${sport.key}: ${sport.name}`);
}

const now = new Date().toISOString().slice(0, 19) + "Z";
const games = (await get("/odds", { league: LEAGUE, markets: "winner", limit: 1, starts_after: now })).data;
if (!games.length) {
  console.log(`\nNo upcoming ${LEAGUE} game has winner prices right now. Try another SOCKODDS_LEAGUE.`);
} else {
  const game = games[0];
  console.log(`\nNext ${LEAGUE} game: ${game.name}, starts ${game.scheduled_start} (${game.status})`);
  for (const market of game.markets) {
    if (market.key !== "winner" || market.period !== "full") continue;
    for (const outcome of market.outcomes) {
      const best = outcome.prices[0]; // prices are sorted best first
      console.log(
        `  ${outcome.name}: best ${best.decimal_odds.toFixed(2)} at ${best.bookmaker}, ` +
          `${outcome.prices.length} bookmaker(s) quoting, seen ${best.observed_at}`,
      );
    }
  }
}

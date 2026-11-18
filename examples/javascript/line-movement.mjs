// Track line movement: how each bookmaker's winner price moved over a window, from recorded history.
//
//   export SOCKODDS_API_KEY="your-key"     # Pro plan (history): https://sockodds.com/pricing/
//   node line-movement.mjs EVENT_ID [FROM TO]
//
// FROM and TO are UTC times such as 2026-12-05T00:00:00Z; the default is the last 8 hours. A window
// may be at most 24 hours. Rows have kind opened, changed or withdrawn (a withdrawal has no price).
// Node 18+, no dependencies. Mirrors https://sockodds.com/docs/examples/line-movement/

const BASE = (process.env.SOCKODDS_BASE_URL ?? "https://api.sockodds.com/v1").replace(/\/$/, "");
const KEY = process.env.SOCKODDS_API_KEY;

// GET a SockOdds route (or a full links.next URL) and return the JSON body.
async function get(path, params = {}) {
  let url = path.startsWith("http") ? path : BASE + path;
  const query = new URLSearchParams(params).toString();
  if (query) url += "?" + query;
  const response = await fetch(url, { headers: { Authorization: `Bearer ${KEY}`, Accept: "application/json" } });
  if (!response.ok) {
    // errors are application/problem+json
    const problem = await response.json().catch(() => ({}));
    let message = `${problem.title ?? response.statusText}: ${problem.detail ?? ""}`;
    if (response.status === 403) message += " (recorded history is on the Pro plan: https://sockodds.com/pricing/)";
    console.error(`HTTP ${response.status} from ${url.split("?")[0]}: ${message}`);
    process.exit(1);
  }
  return response.json();
}

if (!KEY) {
  console.error("Set SOCKODDS_API_KEY first. Get a free key at https://sockodds.com/signup/");
  process.exit(1);
}
const eventId = process.argv[2] || process.env.SOCKODDS_EVENT_ID;
if (!eventId) {
  console.error("Usage: node line-movement.mjs EVENT_ID [FROM TO]");
  process.exit(1);
}
const stamp = (date) => date.toISOString().slice(0, 19) + "Z";
const now = new Date();
const from = process.argv[4] ? process.argv[3] : stamp(new Date(now.getTime() - 8 * 3600 * 1000));
const to = process.argv[4] ? process.argv[4] : stamp(now);

// First and latest price per bookmaker, side and period. Rows arrive oldest first.
const moves = new Map();
let body = await get("/odds/history", { event_id: eventId, from, to, markets: "winner", limit: 250 });
while (true) {
  for (const row of body.data) {
    if (row.decimal_odds === null) continue; // a withdrawal has no price
    const key = `${row.bookmaker}|${row.outcome.side}|${row.market.period}`;
    const move = moves.get(key) ?? { bookmaker: row.bookmaker, name: row.outcome.name, first: row.decimal_odds, changes: 0 };
    move.latest = row.decimal_odds;
    move.at = row.observed_at;
    move.changes += row.kind === "changed" ? 1 : 0;
    moves.set(key, move);
  }
  if (!body.links.next) break;
  body = await get(body.links.next);
}

if (!moves.size) console.log("No recorded winner prices in this window.");
for (const key of [...moves.keys()].sort()) {
  const m = moves.get(key);
  const diff = m.latest - m.first;
  const sign = diff > 0 ? "+" : "";
  console.log(
    `${m.bookmaker.padEnd(14)} ${m.name.padEnd(14)} ${m.first.toFixed(2)} to ${m.latest.toFixed(2)} ` +
      `(${sign}${diff.toFixed(2)}), changes: ${m.changes}, latest ${m.at}`,
  );
}

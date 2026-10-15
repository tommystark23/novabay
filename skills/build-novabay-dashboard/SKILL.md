---
name: build-novabay-dashboard
description: Build a local NovaBay eBay seller dashboard (one HTML file plus a read-only sync) that shows active listings, bids, watchers, sales and orders. Use when an eBay seller wants a personal command-deck dashboard for their own store, or wants to check listings, bids, sales or orders with the novabay-ebay MCP tools.
---

# Build a NovaBay dashboard

NovaBay is a local eBay "command deck": **one HTML file** that opens straight from disk in a browser, fed by a **read-only** data file. No hosting, no database, no paid services.

This plugin ships:
- `novabay-ebay` MCP server: `list_active_listings`, `get_recent_sales`, `get_orders`, `get_seller_summary` (read-only, buyer PII removed).
- `dashboard/index.html` + `dashboard/demo-data.js`: a working template that renders sample data.

## Hard rules
- The seller does every sign-in, keyset creation, consent click and 2FA code. Never type their passwords.
- eBay keys live only in the plugin variables or a private env file (mode 600) outside any cloud-synced folder, repo, log or chat. Never write keys or tokens into HTML/JS/JSON.
- Read-only toward eBay. Never list, revise, relist or end listings, and never message buyers, unless the seller explicitly asks and approves the exact action with a different tool.
- Never write buyer names, usernames, addresses, emails or phone numbers into dashboard files.
- Before replacing an existing `index.html`, copy it into `backup/`.

## 1. Ask first
Ask the seller for: the folder to build in, the shop name to show in the header, and whether they have eBay API keys yet. If not, start in demo mode (`NOVABAY_DEMO=1`) and show them the dashboard with sample data while they get keys (see the plugin README).

## 2. File layout
```
NovaBay/
  index.html          copied from the plugin's dashboard/index.html
  novabay-live.js     window.NOVABAY_LIVE = {...};  (written every refresh)
  backup/
```
**Why a `.js` file and not JSON:** browsers block `fetch()` of local files over `file://`. The page loads `novabay-live.js` with a `<script>` tag and re-injects it every 30 s with a `?t=` cache-buster. Remove the `demo-data.js` script tag once live data exists.

## 3. Live data schema (`window.NOVABAY_LIVE`)
```json
{ "ok": true, "source": "ebay-api", "at": "<ISO UTC>", "shop": "<shop name>",
  "active": [ {"item":"<id>","title":"...","type":"Auction|FixedPrice","price":0,"bids":0,"watchers":0,"end":"<ISO>"} ],
  "sold":   [ {"item":"<id>","title":"...","price":0,"date":"<ISO>"} ],
  "orders": [ {"order":"<id>","title":"...","total":0,"status":"paid|waiting payment|shipped"} ] }
```
Map from the MCP tools: `list_active_listings` -> `active` (`end_time` -> `end`), `get_recent_sales` -> `sold`, `get_orders` -> `orders` (`payment_status` PAID + `fulfillment_status` FULFILLED -> `shipped`; PAID -> `paid`; otherwise `waiting payment`).

## 4. Refreshing the data
Option A (agent-driven): call the MCP tools, build the object above, write `novabay-live.js` atomically (write `.tmp`, then rename).
Option B (unattended): a small stdlib Python script on the seller's computer that does the same calls on a loop (every 60 s for listings, every 5-10 min for orders). Run it as a login service only with the seller's OK (LaunchAgent on macOS, `systemd --user` on Linux, Task Scheduler on Windows). Keep calls well under the seller's eBay daily limit; the MCP server caches for 120 s and spaces calls 1 s apart by default.

## 5. Dashboard behavior
- Header counters: LIVE, BIDS, WATCHERS, SOLD (30D), AWAITING PAYMENT.
- Feed badge: DEMO DATA (`source:"demo"`), LIVE, STALE (no update for 5 min), NOT CONNECTED (no file or `ok:false`).
- Tiles: amber glow + bid tag when a listing has bids; red tag when under 1 h left.
- Orders: mint = paid, amber = waiting payment, cyan = shipped.
- Optional polish: item photos, a 3D card wall (three.js, vendored locally), phone layout, a grading view comparing raw vs graded sold comps.

## 6. Checks before handing over
- Open `index.html` with no live file: badge shows DEMO DATA (template) or NOT CONNECTED (demo script removed).
- After one refresh: badge LIVE; spot-check one listing's bids and watchers against eBay Seller Hub.
- Search the folder for `CLIENT_SECRET`, `REFRESH_TOKEN`, `Bearer`, `v^1.1#`: nothing found.
- Search for buyer names or addresses: nothing found.

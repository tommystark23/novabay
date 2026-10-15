# Marketplace submission answers (https://x.ai/bot/marketplace/submit-a-plugin)

| Field | Answer |
|---|---|
| Org handle | `novastation` |
| Website | https://shop.dogtraineroc.com |
| Logo | `assets/logo.png` (1024x1024 PNG, solid dark background plate) |
| List in | Grok Bot + Cursor |
| MCP server URL / public GitHub repo | `https://github.com/tommystark23/novabay` |

## Short description
Read-only eBay seller dashboard: see live bids, watchers, sales and orders, and build a one-file NovaBay command deck for your store.

## Long description
NovaBay connects your agent to your own eBay seller account, read-only. Ask "what has bids right now?", "what do I need to ship?" or "how much did I sell this month?" and get answers straight from eBay's official APIs. It includes a local stdio MCP server (Python standard library, no installs) with four tools: list_active_listings, get_recent_sales, get_orders and get_seller_summary, plus a skill that builds a one-file NovaBay dashboard showing live bids, watchers, orders and sales on a card-style grid.

NovaBay never lists, revises or ends listings and never messages buyers. Buyer names, addresses, emails and phone numbers are stripped before anything reaches the agent. Keys stay in your plugin configuration, calls are rate-limited and cached, and a demo mode lets anyone try it without an eBay account. Built by a sports-card seller for small eBay sellers.

## Testing instructions
No eBay account needed.
1. Install the plugin and set the variable NOVABAY_DEMO=1 (leave eBay keys blank).
2. Ask: "Use NovaBay to list my active listings sorted by bids." Expect 6 sample listings, top one with 5 bids.
3. Ask: "Show NovaBay orders that need shipping." Expect 1 order (DEMO-ORD-1) with no buyer details.
4. Ask: "Get my NovaBay seller summary." Expect 6 active listings, 9 bids, 22 watchers, $142.50 sold in 30 days.
5. Ask: "Build my NovaBay dashboard in a folder called NovaBay." Open index.html; it shows the DEMO DATA badge.
Optional: `python3 server/test_stdio.py` runs every tool over stdio in demo mode.

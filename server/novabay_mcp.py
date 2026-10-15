#!/usr/bin/env python3
"""NovaBay eBay MCP server (stdio, read-only, Python 3 stdlib only).

Tools: list_active_listings, get_recent_sales, get_orders, get_seller_summary.
This server never lists, revises, relists or ends anything on eBay. It only
calls read endpoints: Trading API GetMyeBaySelling and Sell Fulfillment getOrders.

Env:
  EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REFRESH_TOKEN  your own eBay keys
  NOVABAY_DEMO=1        return built-in sample data (no eBay account needed)
  NOVABAY_CACHE_SECONDS cache lifetime per call (default 120)
  NOVABAY_MIN_INTERVAL  minimum seconds between eBay calls (default 1.0)
"""
import base64, datetime as dt, json, os, sys, threading, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
TRADING_URL = "https://api.ebay.com/ws/api.dll"
FULFILL_URL = "https://api.ebay.com/sell/fulfillment/v1/order"
SCOPES = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly"
NS = {"e": "urn:ebay:apis:eBLBaseComponents"}

def env(name, default=""):
    v = os.environ.get(name, default) or default
    return "" if v.startswith("${") else v  # unexpanded plugin placeholder

DEMO = env("NOVABAY_DEMO", "0").lower() in ("1", "true", "yes")
CACHE_SECONDS = float(env("NOVABAY_CACHE_SECONDS", "120"))
MIN_INTERVAL = float(env("NOVABAY_MIN_INTERVAL", "1.0"))

def log(msg):
    sys.stderr.write("[novabay] %s\n" % msg); sys.stderr.flush()

def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ---------------- rate limit + cache ----------------
_lock = threading.Lock(); _last_call = [0.0]; _cache = {}; _calls_today = {"day": None, "n": 0}

def cached(key, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    val = fn(); _cache[key] = (time.time(), val); return val

def _throttle():
    with _lock:
        wait = MIN_INTERVAL - (time.time() - _last_call[0])
        if wait > 0: time.sleep(wait)
        _last_call[0] = time.time()
        day = dt.date.today().isoformat()
        if _calls_today["day"] != day: _calls_today.update(day=day, n=0)
        _calls_today["n"] += 1

def _http(req, retries=2):
    for attempt in range(retries + 1):
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt * 2); continue
            raise RuntimeError("eBay HTTP %s: %s" % (e.code, e.read()[:300].decode("utf8", "replace")))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt * 2); continue
            raise RuntimeError("eBay network error: %s" % getattr(e, "reason", e))

# ---------------- auth ----------------
_token = {"value": None, "exp": 0}

def access_token():
    if _token["value"] and time.time() < _token["exp"] - 120:
        return _token["value"]
    cid, sec, rt = env("EBAY_CLIENT_ID"), env("EBAY_CLIENT_SECRET"), env("EBAY_REFRESH_TOKEN")
    if not (cid and sec and rt):
        raise RuntimeError("eBay keys missing. Set EBAY_CLIENT_ID, EBAY_CLIENT_SECRET and EBAY_REFRESH_TOKEN, or set NOVABAY_DEMO=1 for sample data.")
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": rt, "scope": SCOPES}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + base64.b64encode(("%s:%s" % (cid, sec)).encode()).decode()})
    data = json.loads(_http(req))
    _token.update(value=data["access_token"], exp=time.time() + int(data.get("expires_in", 7200)))
    return _token["value"]

# ---------------- live eBay calls (read-only) ----------------
def trading(call, inner):
    xml = ('<?xml version="1.0" encoding="utf-8"?><%sRequest xmlns="urn:ebay:apis:eBLBaseComponents">%s</%sRequest>'
           % (call, inner, call)).encode()
    req = urllib.request.Request(TRADING_URL, data=xml, method="POST", headers={
        "X-EBAY-API-IAF-TOKEN": access_token(), "X-EBAY-API-CALL-NAME": call,
        "X-EBAY-API-SITEID": "0", "X-EBAY-API-COMPATIBILITY-LEVEL": "1193", "Content-Type": "text/xml"})
    root = ET.fromstring(_http(req))
    if root.findtext("e:Ack", "", NS) == "Failure":
        raise RuntimeError("eBay error: " + (root.findtext(".//e:LongMessage", "", NS) or "unknown"))
    return root

def _duration_s(d):
    """ISO-8601 duration from eBay TimeLeft, e.g. P3DT4H5M6S -> seconds."""
    import re
    m = re.match(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$", d or "")
    if not m or not any(m.groups()): return None
    dd, h, mi, se = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + se

def _end_time(it):
    end = it.findtext("e:ListingDetails/e:EndTime", "", NS)
    if end: return end
    left = _duration_s(it.findtext("e:TimeLeft", "", NS))
    return iso(dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=left)) if left else ""

def _f(el, path):
    try: return float(el.findtext(path, "0", NS) or 0)
    except ValueError: return 0.0

def live_selling():
    def fetch():
        root = trading("GetMyeBaySelling",
            "<ActiveList><Include>true</Include><Pagination><EntriesPerPage>200</EntriesPerPage></Pagination></ActiveList>"
            "<SoldList><Include>true</Include><DurationInDays>60</DurationInDays><Pagination><EntriesPerPage>200</EntriesPerPage></Pagination></SoldList>"
            "<DetailLevel>ReturnAll</DetailLevel>")
        active = []
        for it in root.findall("e:ActiveList/e:ItemArray/e:Item", NS):
            ss = it.find("e:SellingStatus", NS)
            iid = it.findtext("e:ItemID", "", NS)
            active.append({
                "item_id": iid, "title": it.findtext("e:Title", "", NS),
                "type": "Auction" if it.findtext("e:ListingType", "", NS) == "Chinese" else "FixedPrice",
                "price": _f(ss, "e:CurrentPrice") if ss is not None else 0.0,
                "currency": (ss.find("e:CurrentPrice", NS).get("currencyID") if ss is not None and ss.find("e:CurrentPrice", NS) is not None else "USD"),
                "bids": int(ss.findtext("e:BidCount", "0", NS) or 0) if ss is not None else 0,
                "watchers": int(it.findtext("e:WatchCount", "0", NS) or 0),
                "buy_it_now": _f(it, "e:BuyItNowPrice") or None,
                "end_time": _end_time(it),
                "url": it.findtext("e:ListingDetails/e:ViewItemURL", "", NS) or "https://www.ebay.com/itm/" + iid})
        sales = []
        for o in root.findall("e:SoldList/e:OrderTransactionArray/e:OrderTransaction", NS):
            for tx in o.findall(".//e:Transaction", NS):
                it = tx.find("e:Item", NS)
                if it is None: continue
                sales.append({"item_id": it.findtext("e:ItemID", "", NS), "title": it.findtext("e:Title", "", NS),
                              "price": _f(tx, "e:TotalTransactionPrice") or _f(it, "e:SellingStatus/e:CurrentPrice"),
                              "currency": "USD", "sold_at": tx.findtext("e:CreatedDate", "", NS),
                              "paid": bool(tx.findtext("e:PaidTime", "", NS)),
                              "order_id": o.findtext("e:Order/e:OrderID", "", NS) or tx.findtext("e:OrderLineItemID", "", NS)})
        return {"active": active, "sales": sales}
    return cached("selling", fetch)

def live_orders(days):
    def fetch():
        since = iso(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days))
        q = urllib.parse.urlencode({"filter": "creationdate:[%s..]" % since, "limit": "100"})
        req = urllib.request.Request(FULFILL_URL + "?" + q, headers={"Authorization": "Bearer " + access_token()})
        data = json.loads(_http(req))
        out = []
        for o in data.get("orders", []):
            li = (o.get("lineItems") or [{}])[0]
            tot = (o.get("pricingSummary") or {}).get("total") or {}
            # Buyer username, name, address, email and phone are deliberately dropped.
            out.append({"order_id": o.get("orderId"), "item_id": li.get("legacyItemId"), "title": li.get("title"),
                        "items": len(o.get("lineItems") or []), "total": float(tot.get("value", 0) or 0), "total_note": "buyer total excluding sales tax eBay collects and remits",
                        "currency": tot.get("currency", "USD"), "payment_status": o.get("orderPaymentStatus"),
                        "fulfillment_status": o.get("orderFulfillmentStatus"), "created_at": o.get("creationDate")})
        # The Fulfillment API leaves out sales where the buyer has not checked out / paid yet.
        # Add those from the sold list we already fetched (no extra eBay call).
        have = set(x["item_id"] for x in out)
        for s in live_selling()["sales"]:
            if not s.get("paid") and s["item_id"] not in have and (s.get("sold_at") or "") >= since:
                out.append({"order_id": s.get("order_id") or None, "item_id": s["item_id"], "title": s["title"], "items": 1,
                            "total": s["price"], "currency": s.get("currency", "USD"), "payment_status": "AWAITING_PAYMENT",
                            "fulfillment_status": "NOT_STARTED", "created_at": s.get("sold_at")})
        return out
    return cached("orders:%d" % days, fetch)

# ---------------- demo data ----------------
def demo():
    with open(os.path.join(HERE, "demo_data.json")) as f: d = json.load(f)
    now = dt.datetime.now(dt.timezone.utc)
    active = [dict({k: v for k, v in a.items() if k != "end_time_offset_h"},
                   end_time=iso(now + dt.timedelta(hours=a["end_time_offset_h"])),
                   url="https://www.ebay.com/itm/" + a["item_id"]) for a in d["active"]]
    sales = [dict({k: v for k, v in s.items() if k != "sold_days_ago"}, sold_at=iso(now - dt.timedelta(days=s["sold_days_ago"]))) for s in d["sales"]]
    orders = [dict({k: v for k, v in o.items() if k != "days_ago"}, items=1, created_at=iso(now - dt.timedelta(days=o["days_ago"]))) for o in d["orders"]]
    return active, sales, orders

def get_active():
    return demo()[0] if DEMO else live_selling()["active"]

def get_sales():
    return demo()[1] if DEMO else live_selling()["sales"]

def get_orders_data(days):
    return demo()[2] if DEMO else live_orders(days)

# ---------------- tools ----------------
def _seconds_left(end):
    try: return max(0, int((dt.datetime.strptime(end[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc) - dt.datetime.now(dt.timezone.utc)).total_seconds()))
    except Exception: return None

def t_active(a):
    rows = get_active()
    for r in rows: r["seconds_left"] = _seconds_left(r.get("end_time", ""))
    if a.get("only_with_bids"): rows = [r for r in rows if r["bids"] > 0]
    key = a.get("sort", "end_time")
    if key in ("bids", "watchers", "price"): rows.sort(key=lambda r: -(r.get(key) or 0))
    else: rows.sort(key=lambda r: r.get("end_time") or "")
    lim = int(a.get("limit", 100))
    return {"mode": "demo" if DEMO else "live", "count": len(rows), "listings": rows[:lim]}

def t_sales(a):
    days = int(a.get("days", 30))
    cutoff = iso(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days))
    rows = sorted([s for s in get_sales() if (s.get("sold_at") or "") >= cutoff], key=lambda s: s.get("sold_at") or "", reverse=True)
    return {"mode": "demo" if DEMO else "live", "days": days, "count": len(rows),
            "total": round(sum(s["price"] for s in rows), 2), "sales": rows}

def t_orders(a):
    days = int(a.get("days", 30)); st = (a.get("status") or "all").lower()
    rows = get_orders_data(days)
    if st == "awaiting_payment": rows = [o for o in rows if o.get("payment_status") not in ("PAID", "FULLY_REFUNDED")]
    elif st == "to_ship": rows = [o for o in rows if o.get("payment_status") == "PAID" and o.get("fulfillment_status") != "FULFILLED"]
    elif st == "shipped": rows = [o for o in rows if o.get("fulfillment_status") == "FULFILLED"]
    return {"mode": "demo" if DEMO else "live", "count": len(rows), "orders": rows,
            "privacy": "Buyer names, usernames, addresses, emails and phone numbers are never returned."}

def t_summary(a):
    act = get_active(); sales = t_sales({"days": 30}); orders = get_orders_data(30)
    soon = [x for x in act if (lambda s: s is not None and s < 3600)(_seconds_left(x.get("end_time", "")))]
    return {"mode": "demo" if DEMO else "live", "as_of": iso(dt.datetime.now(dt.timezone.utc)),
            "active_listings": len(act), "auctions": sum(1 for x in act if x["type"] == "Auction"),
            "total_bids": sum(x["bids"] for x in act), "total_watchers": sum(x["watchers"] for x in act),
            "listed_value": round(sum(x["price"] for x in act), 2), "ending_within_1h": len(soon),
            "sales_30d_count": sales["count"], "sales_30d_total": sales["total"],
            "orders_awaiting_payment": sum(1 for o in orders if o.get("payment_status") not in ("PAID", "FULLY_REFUNDED")),
            "orders_to_ship": sum(1 for o in orders if o.get("payment_status") == "PAID" and o.get("fulfillment_status") != "FULFILLED"),
            "ebay_calls_today": _calls_today["n"]}

RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}
TOOLS = {
    "list_active_listings": (t_active, "List the seller's active eBay listings with current price, bid count, watchers, end time, seconds left and URL.",
        {"type": "object", "properties": {
            "only_with_bids": {"type": "boolean", "description": "Only listings with at least one bid."},
            "sort": {"type": "string", "enum": ["end_time", "bids", "watchers", "price"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500}}}),
    "get_recent_sales": (t_sales, "Recent sold items with price and sale time.",
        {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 60, "default": 30}}}),
    "get_orders": (t_orders, "Recent orders with payment and shipping status. Never includes buyer personal data.",
        {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 30},
            "status": {"type": "string", "enum": ["all", "awaiting_payment", "to_ship", "shipped"]}}}),
    "get_seller_summary": (t_summary, "One-shot seller summary: active listings, bids, watchers, 30-day sales, orders to ship or awaiting payment.",
        {"type": "object", "properties": {}}),
}

def handle(msg):
    m, mid, p = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if m == "initialize":
        return {"protocolVersion": p.get("protocolVersion", "2024-11-05"), "capabilities": {"tools": {}},
                "serverInfo": {"name": "novabay-ebay", "version": VERSION}}
    if m == "ping": return {}
    if m == "tools/list":
        return {"tools": [{"name": n, "description": d, "inputSchema": s, "annotations": RO} for n, (_, d, s) in TOOLS.items()]}
    if m == "tools/call":
        name = p.get("name")
        if name not in TOOLS: raise KeyError("Unknown tool: %s" % name)
        try:
            res = TOOLS[name][0](p.get("arguments") or {})
            return {"content": [{"type": "text", "text": json.dumps(res, indent=1)}], "structuredContent": res}
        except Exception as e:
            return {"content": [{"type": "text", "text": "Error: %s" % e}], "isError": True}
    raise LookupError(m)

def main():
    log("started (%s mode)" % ("demo" if DEMO else "live"))
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: msg = json.loads(line)
        except ValueError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if "id" not in msg: continue  # notification
            try: out = {"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg)}
            except LookupError as e: out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Method not found: %s" % e}}
            except Exception as e: out = {"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32602, "message": str(e)}}
        sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()

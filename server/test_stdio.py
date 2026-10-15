"""Smoke test: start the server in demo mode and call every tool over stdio."""
import json, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
p = subprocess.Popen([sys.executable, os.path.join(here, "novabay_mcp.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     env=dict(os.environ, NOVABAY_DEMO="1"), text=True)
def rpc(i, method, params=None):
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}}) + "\n"); p.stdin.flush()
    return json.loads(p.stdout.readline())
assert rpc(1, "initialize", {"protocolVersion": "2025-06-18"})["result"]["serverInfo"]["name"] == "novabay-ebay"
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
names = [t["name"] for t in rpc(2, "tools/list")["result"]["tools"]]
print("tools:", names)
ok = True
for i, (n, a) in enumerate([("list_active_listings", {"sort": "bids"}), ("get_recent_sales", {"days": 30}),
                            ("get_orders", {"status": "all"}), ("get_seller_summary", {})], 3):
    r = rpc(i, "tools/call", {"name": n, "arguments": a})["result"]
    good = not r.get("isError") and r["structuredContent"]["mode"] == "demo"
    ok &= good
    print("PASS" if good else "FAIL", n, json.dumps(r["structuredContent"])[:160])
bad = rpc(9, "tools/call", {"name": "end_listing", "arguments": {}})
print("PASS unknown/write tool rejected" if "error" in bad else "FAIL write tool")
p.stdin.close(); p.wait()
sys.exit(0 if ok and "error" in bad else 1)

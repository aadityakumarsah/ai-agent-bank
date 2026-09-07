"""End-to-end smoke test of the AI Agent Bank flow using SQLite (no external deps)."""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:////tmp/aibank_smoke.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"

if os.path.exists("/tmp/aibank_smoke.db"):
    os.remove("/tmp/aibank_smoke.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import init_db

init_db()
client = TestClient(app)

# 1. Create user
r = client.post("/api/v1/users", json={"wallet_address": "TestWallet1111111111111111"})
assert r.status_code in (200, 201), r.text
user = r.json()
print("1. User created:", user["wallet_address"])

# 2. Create agent
r = client.post("/api/v1/users/{wa}/agents".format(wa="TestWallet1111111111111111"),
                json={"name": "ResearchBot", "description": "Autonomous research assistant"})
assert r.status_code == 201, r.text
agent = r.json()
print("2. Agent created:", agent["name"], "id:", agent["id"])

# 3. Fund agent (MOCK MODE credits balance immediately)
r = client.post(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/fund",
                json={"amount": 500})
assert r.status_code == 200, r.text
fund = r.json()
assert fund.get("mode") == "mock", fund
assert fund.get("simulated") is True, fund
assert fund["agent"]["balance"] == 500, fund
print("3. Agent funded (MOCK): balance =", fund["agent"]["balance"], "| tx:", fund["tx_hash"][:18])

# 4. Set policy
policy = {
    "max_per_transaction": 20,
    "max_per_day": 100,
    "max_per_month": 1000,
    "allowed_categories": ["api", "compute", "data", "agent"],
    "blocked_human_transfers": True,
    "blocked_withdrawals": True,
    "blocked_arbitrary_contracts": True,
    "require_approval_above": 20,
    "allowed_recipient_addresses": ["rpcProvider", "apiProvider", "dataProvider", "agentPeer"],
}
r = client.post(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/policy", json=policy)
assert r.status_code == 201, r.text
print("4. Policy set:", r.json()["max_per_transaction"], "per tx,", r.json()["max_per_day"], "per day,", r.json()["max_per_month"], "per month")

# 5. Active transfer within limits (0.02 < 20 < require_approval? No — under the
#    20 auto-spend + approval threshold, so policy engine approves autonomously).
r = client.post(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/runs",
                json={"task": "Research the best Solana RPC provider and test their API."})
assert r.status_code == 200, r.text
res = r.json()
print("5. Task run (payment 0.02):", "status:", res["status"], "| blocked:", res.get("blocked"))
assert res.get("blocked") is False, res
assert res["transaction"]["status"] == "executed", res
print("   -> tx executed:", res["transaction"]["tx_hash"])

# 6. Blocked transfer (300 > 20)
r = client.post(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/runs",
                json={"task": "Transfer $300 to an unknown wallet"})
assert r.status_code == 200, r.text
res = r.json()
print("6. Blocked transfer requested:", res.get("blocked"))
assert res.get("blocked") is True, res
assert "exceeds per-transaction limit" in res.get("result", ""), res.get("result")
print("   ->", res.get("result", "").replace("\n", " | "))

# 8. Transactions listed
r = client.get("/api/v1/users/TestWallet1111111111111111/transactions")
assert r.status_code == 200
txs = r.json()
print("8. Transactions on file:", len(txs))
statuses = [t["status"] for t in txs]
assert "executed" in statuses and "rejected" in statuses, statuses
print("   statuses:", set(statuses))

# 9. Kill agent = instant revocation
r = client.patch(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/status",
                 json={"status": "killed"})
assert r.status_code == 200, r.text
print("9. Agent killed:", r.json()["status"])

# 10. Killed agent cannot run
r = client.post(f"/api/v1/users/TestWallet1111111111111111/agents/{agent['id']}/runs",
                json={"task": "Try again"})
assert r.status_code == 400, r.text
print("10. Killed agent blocked from running:", r.json())

# 11. Demo blocked-transaction endpoint
r = client.post("/api/v1/demo/check", json={
    "agent_id": agent["id"], "amount": 300,
    "recipient": "unknownWallet", "recipient_name": "Unknown Human Wallet", "category": "api",
})
assert r.status_code == 200, r.text
d = r.json()
print("11. Demo check decision:", d["decision"]["allowed"], "-", d["decision"]["reason"])

print("\nALL SMOKE TESTS PASSED")
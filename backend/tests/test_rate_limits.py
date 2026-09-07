"""Rate limiting (both the Redis-backed check and the TTL-honoring in-memory
fallback) and the demo/api/demo rate limiters."""
import time

from app.services.redis_service import RedisClient


def test_in_memory_ttl_expires(client):
    rn = RedisClient()
    rn.redis = None  # force in-memory fallback
    rn.set("mem:key", "v", ex=1)
    assert rn.get("mem:key") == "v"
    assert rn.ttl("mem:key") >= 0
    time.sleep(1.1)
    assert rn.get("mem:key") is None


def test_in_memory_rate_limit_window_resets(client):
    rn = RedisClient()
    rn.redis = None
    # limit 3 per 1s
    for _ in range(3):
        assert rn.rate_limit_check("mem:rl", 3, 1) is True
    assert rn.rate_limit_check("mem:rl", 3, 1) is False
    time.sleep(1.1)
    # window reset -> allowed again
    assert rn.rate_limit_check("mem:rl", 3, 1) is True


def test_task_run_rate_limit_429(client):
    # create + fund + policy for a fresh agent
    wallet = "wallet_ratelimited"
    client.post("/api/v1/users", json={"wallet_address": wallet})
    r = client.post(f"/api/v1/users/{wallet}/agents", json={"name": "RapidBot"})
    agent = r.json()
    # 10 allowed per minute; the 11th is a 429.
    for i in range(10):
        resp = client.post(
            f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
            json={"task": f"quick check {i}"},
        )
        assert resp.status_code == 200
    blocked = client.post(
        f"/api/v1/users/{wallet}/agents/{agent['id']}/runs",
        json={"task": "spam"},
    )
    assert blocked.status_code == 429
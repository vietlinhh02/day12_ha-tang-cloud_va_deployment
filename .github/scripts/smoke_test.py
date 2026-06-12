"""
Smoke tests cho CI/CD pipeline.
Kiểm tra nhanh tất cả endpoints của production agent.
Chạy: python .github/scripts/smoke_test.py
"""
import threading
import time
import json
import sys

import httpx
import uvicorn

sys.path.insert(0, "06-lab-complete")
from app.main import app

BASE_URL = "http://localhost:8000"


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_graceful_shutdown=5)


def main():
    # Start server
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(4)

    client = httpx.Client(base_url=BASE_URL, timeout=10)
    passed = 0
    total = 5

    # Test 1: GET /health
    r = client.get("/health")
    assert r.status_code == 200, f"/health: {r.status_code}"
    assert r.json()["status"] == "ok"
    print(f"  ✅ GET /health — 200 OK")
    passed += 1

    # Test 2: GET /ready
    r = client.get("/ready")
    assert r.status_code == 200
    print(f"  ✅ GET /ready — 200 OK")
    passed += 1

    # Test 3: POST /ask — NO key → 401
    r = client.post("/ask", json={"question": "hi"})
    assert r.status_code == 401, f"/ask (no key): {r.status_code}"
    print(f"  ✅ POST /ask (no key) → 401 — OK")
    passed += 1

    # Test 4: POST /ask — WITH key → 200
    r = client.post(
        "/ask",
        json={"question": "hello"},
        headers={"X-API-Key": "dev-key-change-me"},
    )
    assert r.status_code == 200, f"/ask (with key): {r.status_code}"
    assert "answer" in r.json()
    print(f"  ✅ POST /ask (with key) → 200 — OK")
    passed += 1

    # Test 5: Rate limit (21 req, limit 20)
    limited = False
    for i in range(21):
        r = client.post(
            "/ask",
            json={"question": f"t{i}"},
            headers={"X-API-Key": "dev-key-change-me"},
        )
        if r.status_code == 429:
            limited = True
    assert limited, "Rate limiter did not trigger!"
    print(f"  ✅ Rate limit (429 after 20 req) — OK")
    passed += 1

    print(f"\n  Result: {passed}/{total} tests passed")
    if passed == total:
        print("  🎉 All smoke tests passed!")
    else:
        print("  ❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

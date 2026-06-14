"""End-to-end smoke test against a running API as a real user.

Drives the exact endpoints the web UI calls: login -> /me -> POST /lead-search ->
poll status -> export leads CSV. Hits live SerpAPI/LLM and the real DB, so it
consumes the account's quota/credits — keep the limit small.

Credentials come from the environment (never hardcode):
    E2E_EMAIL, E2E_PASSWORD   required
    E2E_BASE                  default http://127.0.0.1:8000/api/v1
    E2E_QUERY / E2E_CITY      default "стоматологии" / "Казань"
    E2E_LIMIT                 default 3

Run (from backend/):
    E2E_EMAIL=... E2E_PASSWORD=... python scripts/e2e_real_user.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8000/api/v1")
EMAIL = os.environ.get("E2E_EMAIL")
PASSWORD = os.environ.get("E2E_PASSWORD")
QUERY = os.environ.get("E2E_QUERY", "стоматологии")
CITY = os.environ.get("E2E_CITY", "Казань")
LIMIT = int(os.environ.get("E2E_LIMIT", "3"))
POLL_TIMEOUT_S = int(os.environ.get("E2E_POLL_TIMEOUT", "240"))

DONE_STAGES = {"done", "partial", "failed"}


def _step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


async def main() -> int:
    if not EMAIL or not PASSWORD:
        print("E2E_EMAIL and E2E_PASSWORD env vars are required", file=sys.stderr)
        return 2

    async with httpx.AsyncClient(timeout=30) as c:
        _step("1. login")
        r = await c.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
        if r.status_code != 200 or "access_token" not in r.json():
            print(f"LOGIN FAILED: {r.status_code} {r.text[:200]}")
            return 1
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        print(f"logged in as {EMAIL}")

        _step("2. GET /me")
        me = (await c.get(f"{BASE}/me", headers=headers)).json()
        print(
            f"plan={me.get('plan')} ai_credits={me.get('ai_credits_balance')} "
            f"leads_quota={me.get('leads_quota')}"
        )

        _step(f"3. POST /lead-search  query={QUERY!r} city={CITY!r} limit={LIMIT}")
        r = await c.post(
            f"{BASE}/lead-search",
            headers=headers,
            json={"query": QUERY, "city": CITY, "limit": LIMIT, "fast_mode": True},
        )
        if r.status_code != 202:
            print(f"SEARCH START FAILED: {r.status_code} {r.text[:300]}")
            return 1
        log_id = r.json()["log_id"]
        print(f"log_id={log_id} status={r.json().get('status')}")

        _step("4. poll status")
        deadline = time.monotonic() + POLL_TIMEOUT_S
        status: dict = {}
        while time.monotonic() < deadline:
            status = (await c.get(f"{BASE}/lead-search/{log_id}", headers=headers)).json()
            prog = status.get("progress") or status
            stage = prog.get("stage") or status.get("outcome")
            print(
                f"  [{int(time.monotonic() - (deadline - POLL_TIMEOUT_S)):>3}s] stage={stage} "
                f"found={prog.get('found')} filtered={prog.get('filtered')} "
                f"crawled={prog.get('crawled')} saved={prog.get('saved')} "
                f"llm_calls={prog.get('llm_calls')}",
                flush=True,
            )
            if stage in DONE_STAGES:
                break
            await asyncio.sleep(5)
        else:
            print("TIMEOUT waiting for search to finish")
            return 1

        _step("5. export leads CSV")
        csv_resp = await c.get(f"{BASE}/lead-search/{log_id}/export.csv", headers=headers)
        rows = [line for line in csv_resp.text.splitlines() if line.strip()]
        data_rows = rows[1:] if rows else []
        print(f"leads in CSV: {len(data_rows)}")
        for line in rows[:6]:
            print("  " + line[:160])

        prog = status.get("progress") or status
        saved = int(prog.get("saved") or 0)
        stage = prog.get("stage") or status.get("outcome")
        _step("RESULT")
        ok = stage in {"done", "partial"} and saved >= 1
        print(
            f"stage={stage} saved={saved} leads_csv={len(data_rows)} -> "
            f"{'PASS' if ok else 'FAIL'}"
        )
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

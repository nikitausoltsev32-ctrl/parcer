# backend/scripts/run_funnel_diagnostic.py
"""Run niches through the real lead pipeline and print a funnel diagnostic.

Usage (from backend/):
    python scripts/run_funnel_diagnostic.py \
        --niche "стоматологии" --niche "автосервисы" \
        --city "Екатеринбург" --limit 20 \
        --offer "разработка и доработка сайтов" --business "веб-студия" \
        --csv funnel.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.funnel import compute_funnel, format_funnel_table, funnel_to_csv_rows
from app.services.leads.pipeline import run_lead_search

DIAGNOSTIC_EMAIL = "funnel-diagnostic@internal.local"


async def _get_or_create_user(db, *, offer: str, business: str, city: str | None) -> User:
    user = (
        await db.execute(select(User).where(User.email == DIAGNOSTIC_EMAIL))
    ).scalar_one_or_none()
    profile = {"offer": offer, "business": business, "city": city}
    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=DIAGNOSTIC_EMAIL,
            password_hash="diagnostic-no-login",
            plan="pro",  # enables deep_ai so we measure honest scores
            ai_credits_balance=1_000_000,
            leads_quota=1_000_000,
            llm_consent_at=datetime.now(UTC),
            business_profile=profile,
        )
        db.add(user)
    else:
        user.plan = "pro"
        user.ai_credits_balance = 1_000_000
        user.leads_quota = 1_000_000
        user.llm_consent_at = datetime.now(UTC)
        user.business_profile = profile
    await db.commit()
    return user


async def _run(niches, city, limit, offer, business, csv_path):
    stats_list = []
    async with AsyncSessionLocal() as db:
        user = await _get_or_create_user(db, offer=offer, business=business, city=city)
        for niche in niches:
            print(f"[run] {niche} / {city or '-'} (limit={limit}) ...", flush=True)
            result = await run_lead_search(
                db,
                user=user,
                query=niche,
                city=city,
                limit=limit,
                generate_outreach_messages=False,
            )
            log = await db.get(LeadProcessingLog, uuid.UUID(result.log_id))
            meta = (log.meta if log else None) or {}
            stats = compute_funnel(
                niche,
                city,
                urls_found=(log.urls_found if log else 0) or 0,
                urls_after_filter=(log.urls_after_filter if log else 0) or 0,
                urls_crawled=(log.urls_crawled if log else 0) or 0,
                pages_crawled=(log.pages_crawled_total if log else 0) or 0,
                serp_prescreened_out=meta.get("serp_prescreened_out", 0),
                icp_rejected_out=meta.get("icp_rejected_out", 0),
                history_skipped_out=meta.get("history_skipped_out", 0),
                leads=result.leads,
            )
            stats_list.append(stats)
            print(
                f"[done] {niche}: saved={stats.saved} channel={stats.with_any_channel} "
                f"personal_email={stats.with_personal_email} score70={stats.score_70_plus}",
                flush=True,
            )

    print("\n" + format_funnel_table(stats_list))

    if csv_path:
        rows = funnel_to_csv_rows(stats_list)
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nCSV written: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lead pipeline funnel diagnostic")
    parser.add_argument("--niche", action="append", dest="niches", required=True, help="repeatable")
    parser.add_argument("--city", default=None)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offer", default="разработка и доработка сайтов")
    parser.add_argument("--business", default="веб-студия")
    parser.add_argument("--csv", dest="csv_path", default=None)
    args = parser.parse_args()
    asyncio.run(
        _run(args.niches, args.city, args.limit, args.offer, args.business, args.csv_path)
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.pipeline import run_lead_search
from app.services.leads.policy import effective_search_limit


class LeadSearchQuotaExceededError(Exception):
    pass


async def start_lead_search_job(
    db: AsyncSession,
    *,
    user: User,
    query: str,
    city: str | None,
    limit: int,
    list_name: str | None = None,
    generate_outreach_messages: bool = False,
    fast_mode: bool = True,
    ai_model: str | None = None,
) -> uuid.UUID:
    pre_log_id = uuid.uuid4()
    target_limit = effective_search_limit(
        requested_limit=limit,
        fast_mode=fast_mode,
        leads_quota=user.leads_quota,
    )
    if target_limit <= 0:
        raise LeadSearchQuotaExceededError("Lead search quota is exhausted")
    queued_label = "Поиск поставлен в очередь"
    queued_metrics = {
        "percent": 1,
        "found": 0,
        "filtered": 0,
        "crawled": 0,
        "saved": 0,
        "target": target_limit,
        "pages_crawled": 0,
        "llm_calls": 0,
    }
    pre_log = LeadProcessingLog(
        id=pre_log_id,
        user_id=user.id,
        search_query_original=query,
        outcome="pending",
        meta={
            "city": city,
            "limit": target_limit,
            "requested_limit": limit,
            "fast_mode": fast_mode,
            "ai_model": ai_model,
            "plan": user.plan,
            "saved_leads": 0,
            "progress": {
                "stage": "queued",
                "label": "Поиск поставлен в очередь",
                "percent": 1,
                "found": 0,
                "filtered": 0,
                "crawled": 0,
                "saved": 0,
                "target": target_limit,
                "pages_crawled": 0,
                "llm_calls": 0,
                "current_domain": None,
            },
        },
    )
    pre_log.meta["events"] = [
        {
            "ts": datetime.now(UTC).isoformat(),
            "stage": "queued",
            "message": queued_label,
            "domain": None,
            "status": "queued",
            "label": pre_log.meta["progress"]["label"],
            "api": "Supabase",
            "actor": "LeadSearchJob",
            "tool": "lead_search",
            "metrics": queued_metrics,
        }
    ]
    db.add(pre_log)
    await db.commit()

    user_id = user.id

    async def _run_bg() -> None:
        async with AsyncSessionLocal() as bg_db:
            bg_user = await bg_db.get(User, user_id)
            if bg_user is None:
                return
            try:
                await run_lead_search(
                    bg_db,
                    user=bg_user,
                    query=query,
                    city=city,
                    limit=limit,
                    list_name=list_name,
                    generate_outreach_messages=generate_outreach_messages,
                    pre_log_id=pre_log_id,
                    fast_mode=fast_mode,
                    ai_model=ai_model,
                )
            except Exception as exc:
                async with AsyncSessionLocal() as err_db:
                    err_log = await err_db.get(LeadProcessingLog, pre_log_id)
                    if err_log:
                        err_log.outcome = "failed"
                        err_log.failure_reason = str(exc)[:500]
                        meta = dict(err_log.meta or {})
                        progress = dict(meta.get("progress") or {})
                        progress.update({
                            "stage": "failed",
                            "label": "Поиск завершился с ошибкой",
                            "percent": 100,
                        })
                        meta["progress"] = progress
                        meta["events"] = [
                            *list(meta.get("events") or [])[-19:],
                            {"stage": "failed", "message": str(exc)[:180], "domain": None},
                        ]
                        meta["events"][-1].update(
                            {
                                "ts": datetime.now(UTC).isoformat(),
                                "status": "failed",
                                "label": progress["label"],
                                "api": "Supabase",
                                "actor": "LeadSearchJob",
                                "tool": "lead_search",
                                "metrics": {
                                    "percent": 100,
                                    "found": progress.get("found", 0),
                                    "filtered": progress.get("filtered", 0),
                                    "crawled": progress.get("crawled", 0),
                                    "saved": progress.get("saved", 0),
                                    "target": progress.get("target", target_limit),
                                    "pages_crawled": progress.get("pages_crawled", 0),
                                    "llm_calls": progress.get("llm_calls", 0),
                                },
                            }
                        )
                        err_log.meta = meta
                        await err_db.commit()

    asyncio.create_task(_run_bg())
    return pre_log_id

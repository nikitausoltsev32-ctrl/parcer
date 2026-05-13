import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.lead import Lead, LeadList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.schemas.lead_search import LeadSearchCreate
from app.services.leads.async_search import LeadSearchQuotaExceededError, start_lead_search_job
from app.services.leads.pipeline import _lead_to_dict
from app.services.llm.factory import is_available_model_override

router = APIRouter(prefix="/lead-search", tags=["lead-search"])


def _fallback_progress(log: LeadProcessingLog, meta: dict) -> dict:
    progress = meta.get("progress")
    if isinstance(progress, dict):
        return progress

    target = int(meta.get("limit") or meta.get("saved_leads") or 0)
    saved = int(meta.get("saved_leads") or 0)
    stage = {
        "pending": "queued",
        "success": "done",
        "partial": "partial",
        "failed": "failed",
    }.get(log.outcome, log.outcome)
    label = {
        "queued": "Поиск поставлен в очередь",
        "done": "Поиск завершен",
        "partial": "Поиск завершен частично",
        "failed": "Поиск завершился с ошибкой",
    }.get(stage, stage)
    return {
        "stage": stage,
        "label": label,
        "percent": 100 if stage in {"done", "partial", "failed"} else 1,
        "found": log.urls_found or 0,
        "filtered": log.urls_after_filter or 0,
        "crawled": log.urls_crawled or 0,
        "saved": saved,
        "target": target,
        "pages_crawled": log.pages_crawled_total or 0,
        "llm_calls": len(log.llm_calls or []),
        "current_domain": None,
    }


@router.post("", status_code=202)
async def create_lead_search(
    body: LeadSearchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parsed = body
    if parsed.ai_model and not is_available_model_override(parsed.ai_model):
        raise HTTPException(status_code=422, detail="Selected AI model is not available")
    try:
        pre_log_id = await start_lead_search_job(
            db,
            user=user,
            query=parsed.query,
            city=parsed.city,
            limit=parsed.limit,
            list_name=parsed.list_name,
            fast_mode=parsed.fast_mode,
            ai_model=parsed.ai_model,
        )
    except LeadSearchQuotaExceededError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "lead_quota_exhausted",
                "message": "Lead search quota is exhausted. Increase quota or upgrade plan.",
            },
        ) from exc
    return {"log_id": str(pre_log_id), "status": "pending"}


@router.get("/logs")
async def list_search_logs(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(LeadProcessingLog)
        .where(LeadProcessingLog.user_id == user.id)
        .order_by(LeadProcessingLog.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(log.id),
            "search_query_original": log.search_query_original,
            "city": (log.meta or {}).get("city"),
            "urls_after_filter": log.urls_after_filter,
            "outcome": log.outcome,
            "list_name": (log.meta or {}).get("list_name"),
            "duration_ms": getattr(log, "duration_ms", None),
            "created_at": log.created_at.isoformat(),
        }
        for log in rows.scalars().all()
    ]


@router.get("/{log_id}")
async def get_search_status(
    log_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        lid = uuid.UUID(log_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid log_id")
    log = await db.get(LeadProcessingLog, lid)
    if not log or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    meta = log.meta or {}
    list_id = meta.get("lead_list_id")
    leads: list[dict] = []
    if list_id:
        try:
            lid = uuid.UUID(str(list_id))
        except ValueError:
            lid = None
        if lid is not None:
            lead_rows = await db.execute(
                select(Lead)
                .where(Lead.user_id == user.id, Lead.list_id == lid)
                .order_by(Lead.created_at.asc())
            )
            leads = [_lead_to_dict(lead) for lead in lead_rows.scalars().all()]

    list_name = meta.get("list_name")
    if list_id and not list_name:
        try:
            lead_list = await db.get(LeadList, uuid.UUID(str(list_id)))
        except ValueError:
            lead_list = None
        if lead_list and lead_list.user_id == user.id:
            list_name = lead_list.name

    return {
        "log_id": str(log.id),
        "status": log.outcome,
        "list_id": list_id,
        "list_name": list_name,
        "saved": meta.get("saved_leads", 0),
        "leads": leads,
        "urls_crawled": log.urls_crawled,
        "progress": _fallback_progress(log, meta),
        "events": list(meta.get("events") or [])[-20:],
        "duration_ms": log.duration_ms,
        "failure_reason": log.failure_reason,
        "created_at": log.created_at.isoformat(),
    }

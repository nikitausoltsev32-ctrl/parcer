from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.contact import ContactList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.schemas.lead_search import LeadSearchCreate, LeadSearchRead
from app.services.leads.pipeline import run_lead_search

router = APIRouter(prefix="/lead-search", tags=["lead-search"])


@router.post("", response_model=LeadSearchRead, status_code=201)
async def create_lead_search(
    body: LeadSearchCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await run_lead_search(
        db,
        user=user,
        query=body.query,
        city=body.city,
        limit=body.limit,
        list_name=body.list_name,
    )
    return LeadSearchRead(
        list_id=result.list_id,
        list_name=result.list_name,
        saved=result.saved,
        contacts=result.contacts,
        log_id=result.log_id,
    )


@router.get("/logs")
async def list_search_logs(
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(LeadProcessingLog, ContactList.name)
        .outerjoin(ContactList, LeadProcessingLog.contact_list_id == ContactList.id)
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
            "list_name": list_name,
            "duration_ms": getattr(log, "duration_ms", None),
            "created_at": log.created_at.isoformat(),
        }
        for log, list_name in rows.all()
    ]

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
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

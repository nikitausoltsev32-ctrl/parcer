from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.campaign import TemplateRead

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRead])
async def list_templates(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Template).where((Template.user_id == user.id) | (Template.user_id.is_(None)))
    )
    return rows.scalars().all()


@router.post("", status_code=501)
async def create_template(user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="Not implemented yet (Phase 3)")

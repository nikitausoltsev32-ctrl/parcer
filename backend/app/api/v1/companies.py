import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    size: str | None = None
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    size: str | None = None
    notes: str | None = None


router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
async def list_companies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Company)
        .where(Company.user_id == user.id)
        .order_by(Company.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "website": c.website,
            "industry": c.industry,
            "city": c.city,
            "size": c.size,
            "created_at": c.created_at.isoformat(),
        }
        for c in rows.scalars()
    ]


@router.post("", status_code=201)
async def create_company(
    body: CompanyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = Company(
        id=uuid.uuid4(),
        user_id=user.id,
        name=body.name,
        website=body.website,
        industry=body.industry,
        city=body.city,
        size=body.size,
        notes=body.notes,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return {
        "id": str(company.id),
        "name": company.name,
        "website": company.website,
        "industry": company.industry,
        "city": company.city,
        "size": company.size,
        "notes": company.notes,
        "created_at": company.created_at.isoformat(),
    }


@router.get("/{company_id}")
async def get_company(
    company_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid company_id")
    row = await db.get(Company, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Company not found")
    return {
        "id": str(row.id),
        "name": row.name,
        "website": row.website,
        "industry": row.industry,
        "city": row.city,
        "size": row.size,
        "notes": row.notes,
        "created_at": row.created_at.isoformat(),
    }


@router.patch("/{company_id}")
async def update_company(
    company_id: str,
    body: CompanyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid company_id")
    row = await db.get(Company, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Company not found")
    
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(row, field, value)
    
    await db.commit()
    await db.refresh(row)
    return {
        "id": str(row.id),
        "name": row.name,
        "website": row.website,
        "industry": row.industry,
        "city": row.city,
        "size": row.size,
        "notes": row.notes,
    }


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        cid = uuid.UUID(company_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid company_id")
    row = await db.get(Company, cid)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.delete(row)
    await db.commit()

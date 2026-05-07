import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.activity import Activity
from app.models.contact import Contact, ContactList
from app.models.user import User
from app.services.crm.contact_import import ContactImportError, confirm_contact_import, preview_contact_import


class ContactUpdate(BaseModel):
    status: str | None = None
    next_step: str | None = None
    next_step_at: datetime | None = None
    email: str | None = None
    phone: str | None = None
    position: str | None = None


class NoteCreate(BaseModel):
    body: str
    meta: dict[str, Any] | None = None


router = APIRouter(tags=["contacts"])


@router.get("/contacts")
async def list_contacts(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Contact, ContactList.source)
        .outerjoin(ContactList, Contact.list_id == ContactList.id)
        .where(Contact.user_id == user.id)
        .order_by(Contact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = []
    for contact, source in rows.all():
        raw = contact.raw or {}
        enrichment = contact.enrichment or {}
        company = raw.get("company") or (raw.get("name") if raw.get("name") != contact.contact_name else None)
        website = enrichment.get("website") or raw.get("website")
        city = enrichment.get("city") or raw.get("city")
        industry = raw.get("industry") or enrichment.get("industry")
        result.append(
            {
                "id": str(contact.id),
                "full_name": contact.contact_name or company or "-",
                "company_name": company,
                "status": contact.status,
                "email": contact.email,
                "phone": contact.phone or raw.get("phone"),
                "source": source or "manual",
                "list_id": str(contact.list_id) if contact.list_id else None,
                "website": website,
                "city": city,
                "industry": industry,
                "enrichment_status": "done"
                if enrichment.get("description") or enrichment.get("website_summary")
                else None,
                "enrichment_summary": enrichment.get("description") or enrichment.get("website_summary"),
                "lead_score": enrichment.get("lead_score"),
                "confidence": enrichment.get("confidence"),
            }
        )
    return result


@router.post("/contacts/import")
async def import_contacts_file(
    file: UploadFile = File(...),
    confirmed: bool = Query(default=False),
    list_name: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "contacts.csv"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Import file is empty")

    try:
        if confirmed:
            return await confirm_contact_import(db, user, filename=filename, content=content, list_name=list_name)
        return await preview_contact_import(
            db,
            user,
            filename=filename,
            content=content,
            content_type=file.content_type,
        )
    except ContactImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/contact-lists/import-csv")
async def import_csv(
    file: UploadFile = File(...),
    list_name: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported on this legacy endpoint")

    content = await file.read()
    try:
        return await confirm_contact_import(db, user, filename=file.filename, content=content, list_name=list_name)
    except ContactImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    body: ContactUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contact = await _get_contact(contact_id, user.id, db)
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(contact, field, value)
    await db.commit()
    return {"id": str(contact.id), **updates}


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contact = await _get_contact(contact_id, user.id, db)
    await db.delete(contact)
    await db.commit()


@router.get("/contacts/{contact_id}/activities")
async def list_activities(
    contact_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_contact(contact_id, user.id, db)
    rows = await db.execute(
        select(Activity)
        .where(Activity.contact_id == uuid.UUID(contact_id), Activity.user_id == user.id)
        .order_by(Activity.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(a.id),
            "type": a.type,
            "body": a.body,
            "meta": a.meta,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows.scalars()
    ]


@router.post("/contacts/{contact_id}/notes", status_code=201)
async def add_note(
    contact_id: str,
    body: NoteCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_contact(contact_id, user.id, db)
    note = Activity(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_id=uuid.UUID(contact_id),
        type="note",
        body=body.body,
        meta=body.meta,
    )
    db.add(note)
    await db.commit()
    return {"id": str(note.id), "type": "note", "body": body.body}


async def _get_contact(contact_id: str, user_id: uuid.UUID, db: AsyncSession) -> Contact:
    try:
        cid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid contact_id")
    row = await db.get(Contact, cid)
    if not row or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    return row


@router.get("/contact-lists")
async def list_contact_lists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(ContactList)
        .where(ContactList.user_id == user.id)
        .order_by(ContactList.created_at.desc())
    )
    return [
        {
            "id": str(cl.id),
            "name": cl.name,
            "source": cl.source,
            "total_count": cl.total_count,
            "created_at": cl.created_at.isoformat(),
        }
        for cl in rows.scalars()
    ]


@router.delete("/contact-lists/{list_id}", status_code=204)
async def delete_contact_list(
    list_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        lid = uuid.UUID(list_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid list_id")
    row = await db.get(ContactList, lid)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="List not found")
    await db.delete(row)
    await db.commit()

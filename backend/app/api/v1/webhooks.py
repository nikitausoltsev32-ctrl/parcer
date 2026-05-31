import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.tracking import verify_webhook_token
from app.models.contact import Contact, ContactList
from app.models.user import User
from app.services.credits import get_balance
from app.workers.main import enrich_contact_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _verified_user(user_id: uuid.UUID, token: str, db: AsyncSession) -> User:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    # Один и тот же ответ для несуществующего пользователя и неверной подписи —
    # чтобы вебхук нельзя было использовать для перебора user_id.
    if not user or not verify_webhook_token(str(user_id), token):
        raise HTTPException(status_code=404, detail="Not found")
    return user


async def _ingest_lead(
    db: AsyncSession,
    user: User,
    *,
    source: str,
    list_name: str,
    lead_name: str,
    email: str | None,
    phone: str | None,
    website: str | None,
    raw: dict,
) -> Contact:
    list_row = await db.execute(
        select(ContactList).where(ContactList.user_id == user.id, ContactList.name == list_name)
    )
    contact_list = list_row.scalar_one_or_none()
    if not contact_list:
        contact_list = ContactList(id=uuid.uuid4(), user_id=user.id, name=list_name, source="integration")
        db.add(contact_list)
        await db.flush()

    contact = Contact(
        id=uuid.uuid4(),
        user_id=user.id,
        list_id=contact_list.id,
        contact_name=lead_name,
        email=email,
        phone=phone,
        status="new",
        enrichment={"website": website} if website else {},
        raw=raw,
    )
    db.add(contact)
    await db.commit()

    if website:
        if await get_balance(db, str(user.id)) > 0:
            await enrich_contact_task.defer_async(contact_id=str(contact.id))
        else:
            logger.info("[webhook:%s] skip enrich for %s — no credits", source, contact.id)

    return contact


@router.post("/amocrm/{user_id}")
@limiter.limit("60/minute")
async def amocrm_webhook(
    user_id: uuid.UUID,
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Вебхук для приёма лидов из amoCRM. URL: /api/v1/webhooks/amocrm/{user_id}?token=..."""
    user = await _verified_user(user_id, token, db)

    form = await request.form()
    lead_name = form.get("leads[add][0][name]") or form.get("name") or "Новый лид (amoCRM)"
    contact_email = form.get("contacts[add][0][custom_fields][EMAIL][0]") or form.get("email")
    contact_phone = form.get("contacts[add][0][custom_fields][PHONE][0]") or form.get("phone")
    website = form.get("website")

    contact = await _ingest_lead(
        db,
        user,
        source="amocrm",
        list_name="Входящие лиды (amoCRM)",
        lead_name=lead_name,
        email=contact_email,
        phone=contact_phone,
        website=website,
        raw={"source": "amocrm", "form_data": dict(form)},
    )
    return {"status": "ok", "contact_id": str(contact.id)}


@router.post("/bitrix24/{user_id}")
@limiter.limit("60/minute")
async def bitrix24_webhook(
    user_id: uuid.UUID,
    request: Request,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Вебхук для приёма лидов из Битрикс24. URL: /api/v1/webhooks/bitrix24/{user_id}?token=..."""
    user = await _verified_user(user_id, token, db)

    try:
        data = await request.json()
    except Exception:
        data = dict(await request.form())

    lead_name = data.get("TITLE") or data.get("name") or "Новый лид (Битрикс24)"
    contact = await _ingest_lead(
        db,
        user,
        source="bitrix24",
        list_name="Входящие лиды (Bitrix24)",
        lead_name=lead_name,
        email=data.get("EMAIL"),
        phone=data.get("PHONE"),
        website=data.get("WEB"),
        raw={"source": "bitrix24", "payload": data},
    )
    return {"status": "ok", "contact_id": str(contact.id)}

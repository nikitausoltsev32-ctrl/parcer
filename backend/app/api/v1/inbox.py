import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.inbox_message import InboxMessage
from app.models.user import User

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("")
async def list_inbox(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(InboxMessage)
        .where(InboxMessage.user_id == user.id)
        .order_by(InboxMessage.created_at.desc())
        .limit(limit)
    )
    msgs = rows.scalars().all()
    return [
        {
            "id": str(m.id),
            "from_email": m.from_email,
            "subject": m.subject,
            "body_text": m.body_text,
            "classification": m.classification,
            "classification_confidence": m.classification_confidence,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "created_at": m.created_at.isoformat(),
            "campaign_id": str(m.campaign_id) if m.campaign_id else None,
            "contact_id": str(m.contact_id) if m.contact_id else None,
        }
        for m in msgs
    ]


@router.patch("/{message_id}")
async def update_classification(
    message_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(InboxMessage).where(
            InboxMessage.id == message_id,
            InboxMessage.user_id == user.id,
        )
    )
    msg = row.scalar_one_or_none()
    if not msg:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    if "classification" in body:
        msg.classification = body["classification"]
    await db.commit()
    return {"ok": True}


@router.post("/{message_id}/reply", status_code=501)
async def reply(message_id: str, user: User = Depends(get_current_user)):
    from fastapi import HTTPException
    raise HTTPException(status_code=501, detail="Not implemented yet")

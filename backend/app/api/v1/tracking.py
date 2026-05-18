import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tracking import verify
from app.models.campaign import Campaign, CampaignMessage
from app.models.contact import Contact
from app.models.event import Event
from app.models.suppression import Suppression

router = APIRouter(prefix="/t", tags=["tracking"], include_in_schema=False)

# 1×1 прозрачный GIF
_PIXEL = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
    0x01, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff,
    0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3b,
])


@router.get("/open/{tracking_id}")
async def track_open(
    tracking_id: uuid.UUID,
    sig: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    tid = str(tracking_id)
    if not verify(tid, sig):
        return Response(content=_PIXEL, media_type="image/gif")

    msg_row = await db.execute(
        select(CampaignMessage).where(CampaignMessage.tracking_id == tracking_id)
    )
    msg = msg_row.scalar_one_or_none()
    if not msg or msg.opened_at:
        return Response(content=_PIXEL, media_type="image/gif")

    from datetime import UTC, datetime
    msg.opened_at = datetime.now(UTC)
    msg.status = "opened"

    camp_row = await db.execute(select(Campaign).where(Campaign.id == msg.campaign_id))
    campaign = camp_row.scalar_one_or_none()
    if campaign:
        stats = dict(campaign.stats or {})
        stats["opened"] = stats.get("opened", 0) + 1
        campaign.stats = stats

    db.add(Event(
        message_id=msg.id,
        campaign_id=msg.campaign_id,
        type="open",
    ))
    await db.commit()
    return Response(content=_PIXEL, media_type="image/gif")


@router.get("/click/{tracking_id}")
async def track_click(
    tracking_id: uuid.UUID,
    sig: str = Query(...),
    url: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    tid = str(tracking_id)
    # Security: Avoid manual unquote since FastAPI already unquotes query parameters.
    destination = url
    if not verify(tid, sig):
        # Security: Do not redirect on invalid signature to prevent Open Redirect
        raise HTTPException(status_code=400, detail="Invalid signature")

    msg_row = await db.execute(
        select(CampaignMessage).where(CampaignMessage.tracking_id == tracking_id)
    )
    msg = msg_row.scalar_one_or_none()
    if msg:
        from datetime import UTC, datetime
        if not msg.clicked_at:
            msg.clicked_at = datetime.now(UTC)
            msg.status = "clicked"
            camp_row = await db.execute(select(Campaign).where(Campaign.id == msg.campaign_id))
            campaign = camp_row.scalar_one_or_none()
            if campaign:
                stats = dict(campaign.stats or {})
                stats["clicked"] = stats.get("clicked", 0) + 1
                campaign.stats = stats
        db.add(Event(message_id=msg.id, campaign_id=msg.campaign_id, type="click", meta={"url": destination}))
        await db.commit()

    return RedirectResponse(url=destination, status_code=302)


@router.get("/unsub/{tracking_id}", response_class=HTMLResponse)
async def track_unsub(
    tracking_id: uuid.UUID,
    sig: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    tid = str(tracking_id)
    if not verify(tid, sig):
        return HTMLResponse("<html><body><p>Ссылка недействительна.</p></body></html>", status_code=400)

    msg_row = await db.execute(
        select(CampaignMessage).where(CampaignMessage.tracking_id == tracking_id)
    )
    msg = msg_row.scalar_one_or_none()
    if not msg:
        return HTMLResponse("<html><body><p>Ссылка не найдена.</p></body></html>", status_code=404)

    camp_row = await db.execute(select(Campaign).where(Campaign.id == msg.campaign_id))
    campaign = camp_row.scalar_one_or_none()

    contact_row = await db.execute(select(Contact).where(Contact.id == msg.contact_id))
    contact = contact_row.scalar_one_or_none()

    if contact and contact.email and campaign:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Suppression).values(
            id=uuid.uuid4(),
            user_id=campaign.user_id,
            email=contact.email,
            reason="unsubscribe",
        ).on_conflict_do_nothing(constraint="uq_suppressions_user_email")
        await db.execute(stmt)
        stats = dict(campaign.stats or {})
        stats["unsub"] = stats.get("unsub", 0) + 1
        campaign.stats = stats
        db.add(Event(message_id=msg.id, campaign_id=campaign.id, type="unsub"))
        await db.commit()

    return HTMLResponse(
        "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
        "<h2>Вы отписаны от рассылки</h2>"
        "<p>Ваш адрес больше не будет получать письма.</p>"
        "</body></html>"
    )

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limit import limiter, user_or_ip_key
from app.models.campaign import Campaign, CampaignMessage
from app.models.contact import ContactList
from app.models.smtp_account import SmtpAccount
from app.models.template import Template
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignMessageRead,
    CampaignMessageUpdate,
    CampaignRead,
    ContactListRead,
)

router = APIRouter(tags=["campaigns"])


@router.get("/contact-lists", response_model=list[ContactListRead])
async def list_contact_lists(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(ContactList).where(ContactList.user_id == user.id))
    return rows.scalars().all()


@router.get("/campaigns", response_model=list[CampaignRead])
async def list_campaigns(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Campaign).where(Campaign.user_id == user.id).order_by(Campaign.created_at.desc())
    )
    return rows.scalars().all()


@router.post("/campaigns", response_model=CampaignRead, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    list_exists = (
        await db.execute(select(ContactList.id).where(ContactList.id == body.list_id, ContactList.user_id == user.id))
    ).scalar_one_or_none()
    if not list_exists:
        raise HTTPException(status_code=400, detail="Unknown list_id")
    smtp_exists = (
        await db.execute(
            select(SmtpAccount.id).where(SmtpAccount.id == body.smtp_account_id, SmtpAccount.user_id == user.id)
        )
    ).scalar_one_or_none()
    if not smtp_exists:
        raise HTTPException(status_code=400, detail="Unknown smtp_account_id")
    template_exists = (
        await db.execute(
            select(Template.id).where(
                Template.id == body.template_id,
                (Template.user_id == user.id) | (Template.user_id.is_(None)),
            )
        )
    ).scalar_one_or_none()
    if not template_exists:
        raise HTTPException(status_code=400, detail="Unknown template_id")

    campaign = Campaign(
        id=uuid.uuid4(),
        user_id=user.id,
        name=body.name,
        list_id=body.list_id,
        template_id=body.template_id,
        smtp_account_id=body.smtp_account_id,
        send_rate_per_hour=body.send_rate_per_hour,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}", response_model=CampaignRead)
async def get_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    return campaign


@router.get("/campaigns/{campaign_id}/messages", response_model=list[CampaignMessageRead])
async def list_messages(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    if not row.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Not found")
    rows = await db.execute(
        select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id)
    )
    return rows.scalars().all()


@router.put("/campaigns/{campaign_id}/messages/{message_id}", response_model=CampaignMessageRead)
async def update_message(
    campaign_id: uuid.UUID,
    message_id: uuid.UUID,
    body: CampaignMessageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Can only edit messages before approval")

    row_msg = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.id == message_id, 
            CampaignMessage.campaign_id == campaign_id
        )
    )
    message = row_msg.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.subject = body.subject
    message.body = body.body
    await db.commit()
    await db.refresh(message)
    return message


@router.post("/campaigns/{campaign_id}/generate")
async def generate_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.workers.main import generate_letters

    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    if campaign.status not in ("draft", "generated"):
        raise HTTPException(status_code=400, detail=f"Cannot generate in status '{campaign.status}'")
    campaign.status = "generating"
    await db.commit()
    await generate_letters.defer_async(campaign_id=str(campaign_id))
    return {"status": "generating"}


@router.post("/campaigns/{campaign_id}/approve")
async def approve_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    if campaign.status != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Cannot approve in status '{campaign.status}'")
    
    campaign.status = "approved"
    await db.commit()
    return {"status": "approved"}



@router.post("/campaigns/{campaign_id}/send")
@limiter.limit("5/minute", key_func=user_or_ip_key)
async def send_campaign_route(
    request: Request,
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.workers.main import send_email

    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    if campaign.status != "approved":
        raise HTTPException(status_code=400, detail=f"Cannot send in status '{campaign.status}'")

    rows = await db.execute(
        select(CampaignMessage).where(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.status == "pending",
        )
    )
    messages = rows.scalars().all()
    rate = max(campaign.send_rate_per_hour, 1)
    for i, msg in enumerate(messages):
        await send_email.defer_async(
            message_id=str(msg.id),
            schedule_in={"seconds": int(3600 / rate) * i},
        )

    campaign.status = "sending"
    await db.commit()
    return {"status": "sending", "enqueued": len(messages)}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    campaign.status = "paused"
    await db.commit()
    return {"status": "paused"}


@router.get("/campaigns/{campaign_id}/stats")
async def campaign_stats(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")
    return campaign.stats


@router.get("/campaigns/{campaign_id}/export.csv")
async def export_campaign_csv(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user.id)
    )
    campaign = row.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Not found")

    from app.models.contact import Contact

    rows = await db.execute(
        select(CampaignMessage, Contact)
        .join(Contact, CampaignMessage.contact_id == Contact.id)
        .where(CampaignMessage.campaign_id == campaign_id)
    )
    results = rows.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Contact Name", "Company", "Email", "Phone", "Status", "Subject", "Sent At"])

    for msg, contact in results:
        company_name = (contact.raw or {}).get("company") or ""
        sent_at = msg.sent_at.isoformat() if msg.sent_at else ""
        writer.writerow([
            contact.contact_name or "",
            company_name,
            contact.email or "",
            contact.phone or "",
            msg.status,
            msg.subject or "",
            sent_at,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}.csv"}
    )

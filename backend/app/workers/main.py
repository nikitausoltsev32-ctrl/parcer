"""Procrastinate worker entry point."""
import asyncio
import smtplib
import ssl
import uuid
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import procrastinate

from app.core.config import settings


def _build_html(body: str, open_url: str, unsub_url: str) -> str:
    import html as _html
    paragraphs = "".join(
        f"<p>{_html.escape(line) if line.strip() else '&nbsp;'}</p>"
        for line in body.splitlines()
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body "
        "style='font-family:Arial,sans-serif;font-size:15px;color:#222;max-width:600px;margin:0 auto;padding:24px'>"
        f"{paragraphs}"
        "<hr style='border:none;border-top:1px solid #eee;margin:24px 0'>"
        f"<p style='font-size:12px;color:#999'>Вы получили это письмо, так как ваш адрес был в списке получателей. "
        f"<a href='{unsub_url}' style='color:#999'>Отписаться</a></p>"
        f"<img src='{open_url}' width='1' height='1' style='display:none' alt=''>"
        "</body></html>"
    )


def _psycopg_conninfo(database_url: str | None = None) -> str:
    url = database_url or settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.pop("pgbouncer", None)
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        conninfo=_psycopg_conninfo(),
        json_dumps=None,
        json_loads=None,
    )
)


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def generate_letters(campaign_id: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.campaign import Campaign, CampaignMessage
    from app.models.contact import Contact
    from app.models.template import Template
    from app.models.user import User
    from app.services.letters.generator import generate_letter

    async with AsyncSessionLocal() as db:
        row = await db.execute(select(Campaign).where(Campaign.id == uuid.UUID(campaign_id)))
        campaign = row.scalar_one_or_none()
        if not campaign:
            return

        try:
            user_row = await db.execute(select(User).where(User.id == campaign.user_id))
            user = user_row.scalar_one()

            tmpl_row = await db.execute(select(Template).where(Template.id == campaign.template_id))
            template = tmpl_row.scalar_one()

            contacts_row = await db.execute(
                select(Contact).where(Contact.list_id == campaign.list_id, Contact.email.isnot(None))
            )
            contacts = contacts_row.scalars().all()

            bp = user.business_profile or {}
            sender = {
                "name": user.full_name or "",
                "business": bp.get("business", ""),
                "offer": bp.get("offer", ""),
                "city": bp.get("city", ""),
            }

            generated = 0
            for contact in contacts:
                enrich = contact.enrichment or {}
                raw = contact.raw or {}
                contact_data = {
                    "company_name": raw.get("company") or contact.contact_name or "",
                    "contact_name": contact.contact_name or "",
                    "website": enrich.get("website", ""),
                    "industry": raw.get("industry", ""),
                    "city": enrich.get("city") or raw.get("city", ""),
                    "website_summary": enrich.get("description") or enrich.get("website_summary", ""),
                }
                try:
                    result = await generate_letter(
                        sender=sender,
                        contact=contact_data,
                        template_name=template.name,
                        template_instruction=template.custom_instruction or "",
                        tone=template.tone,
                    )
                    db.add(CampaignMessage(
                        id=uuid.uuid4(),
                        campaign_id=campaign.id,
                        contact_id=contact.id,
                        subject=result.get("subject", ""),
                        body=result.get("body", ""),
                        status="pending",
                    ))
                    generated += 1
                except Exception as e:
                    db.add(CampaignMessage(
                        id=uuid.uuid4(),
                        campaign_id=campaign.id,
                        contact_id=contact.id,
                        status="failed",
                        error=str(e)[:500],
                    ))

            stats = dict(campaign.stats or {})
            stats["generated"] = generated
            campaign.stats = stats
            campaign.status = "generated"
            await db.commit()
        except Exception as e:
            campaign.status = "failed"
            stats = dict(campaign.stats or {})
            stats["error"] = str(e)[:500]
            campaign.stats = stats
            await db.commit()
            raise


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def send_email(message_id: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.core.fernet import decrypt_password
    from app.models.campaign import Campaign, CampaignMessage
    from app.models.contact import Contact
    from app.models.smtp_account import SmtpAccount
    from app.models.suppression import Suppression

    async with AsyncSessionLocal() as db:
        msg_row = await db.execute(
            select(CampaignMessage).where(CampaignMessage.id == uuid.UUID(message_id))
        )
        msg = msg_row.scalar_one()
        if msg.status != "pending":
            return

        camp_row = await db.execute(select(Campaign).where(Campaign.id == msg.campaign_id))
        campaign = camp_row.scalar_one()

        smtp_row = await db.execute(select(SmtpAccount).where(SmtpAccount.id == campaign.smtp_account_id))
        smtp = smtp_row.scalar_one()

        contact_row = await db.execute(select(Contact).where(Contact.id == msg.contact_id))
        contact = contact_row.scalar_one()

        if not contact.email:
            msg.status = "failed"
            msg.error = "no email"
            await db.commit()
            return

        supp = await db.execute(
            select(Suppression).where(
                Suppression.user_id == campaign.user_id,
                Suppression.email == contact.email,
            )
        )
        if supp.scalar_one_or_none():
            msg.status = "suppressed"
            await db.commit()
            return

        try:
            from app.core import tracking as trk
            tid = str(msg.tracking_id)
            _unsub_url = trk.unsub_url(tid)
            _open_url = trk.open_url(tid)

            plain_body = (
                f"{msg.body}\n\n---\n"
                f"Чтобы отписаться от рассылки: {_unsub_url}"
            )
            html_body = _build_html(msg.body, _open_url, _unsub_url)

            if smtp.oauth_refresh_token:
                from app.services.gmail import send_message as gmail_send
                await gmail_send(smtp, contact.email, msg.subject, plain_body, db,
                                 unsub_url=_unsub_url, html_body=html_body)
            else:
                password = decrypt_password(smtp.password_encrypted)

                def _send() -> None:
                    mime = MIMEMultipart("alternative")
                    mime["Subject"] = msg.subject
                    mime["From"] = f"{smtp.from_name} <{smtp.from_email}>"
                    mime["To"] = contact.email
                    mime["List-Unsubscribe"] = f"<{_unsub_url}>"
                    mime["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
                    mime.attach(MIMEText(plain_body, "plain", "utf-8"))
                    mime.attach(MIMEText(html_body, "html", "utf-8"))
                    ctx = ssl.create_default_context()
                    if smtp.port == 465:
                        with smtplib.SMTP_SSL(smtp.host, smtp.port, context=ctx, timeout=30) as s:
                            s.login(smtp.username, password)
                            s.sendmail(smtp.from_email, contact.email, mime.as_string())
                    else:
                        with smtplib.SMTP(smtp.host, smtp.port, timeout=30) as s:
                            s.ehlo()
                            s.starttls(context=ctx)
                            s.login(smtp.username, password)
                            s.sendmail(smtp.from_email, contact.email, mime.as_string())

                await asyncio.to_thread(_send)

            msg.status = "sent"
            msg.sent_at = datetime.now(UTC)
            stats = dict(campaign.stats or {})
            stats["sent"] = stats.get("sent", 0) + 1
            campaign.stats = stats
        except Exception as e:
            msg.status = "failed"
            msg.error = str(e)
            stats = dict(campaign.stats or {})
            stats["failed"] = stats.get("failed", 0) + 1
            campaign.stats = stats

        await db.commit()


@app.task(queue="default")
async def poll_inbox() -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.inbox_message import InboxMessage
    from app.models.smtp_account import SmtpAccount
    from app.services.gmail import list_unread_messages

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(SmtpAccount).where(
                SmtpAccount.oauth_refresh_token.isnot(None),
                SmtpAccount.is_active.is_(True),
            )
        )
        accounts = rows.scalars().all()

        new_ids: list[str] = []
        for account in accounts:
            try:
                messages = await list_unread_messages(account, db)
            except Exception:
                continue

            for m in messages:
                exists = await db.execute(
                    select(InboxMessage).where(InboxMessage.message_id == m["gmail_id"])
                )
                if exists.scalar_one_or_none():
                    continue

                inbox_msg = InboxMessage(
                    id=uuid.uuid4(),
                    user_id=account.user_id,
                    smtp_account_id=account.id,
                    message_id=m["gmail_id"],
                    from_email=m["from_email"],
                    subject=m["subject"],
                    body_text=m["snippet"],
                    raw=m,
                )
                db.add(inbox_msg)
                new_ids.append(str(inbox_msg.id))

        await db.commit()
        for msg_id in new_ids:
            await classify_inbox_message.defer_async(inbox_message_id=msg_id)


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=2))
async def classify_inbox_message(inbox_message_id: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.inbox_message import InboxMessage
    from app.services.llm.base import LLMMessage
    from app.services.llm.factory import get_llm_client

    _PROMPT = """\
Определи тип ответа на холодное письмо. Верни JSON:
{{"label": "<label>", "confidence": <0..1>}}

Метки: interested | not_interested | auto_reply | question | meeting_request | other

Тема: {subject}
Текст: {body}

Только JSON, без markdown."""

    async with AsyncSessionLocal() as db:
        row = await db.execute(
            select(InboxMessage).where(InboxMessage.id == uuid.UUID(inbox_message_id))
        )
        msg = row.scalar_one_or_none()
        if not msg or msg.classification:
            return

        prompt = _PROMPT.format(
            subject=msg.subject or "",
            body=(msg.body_text or "")[:1000],
        )
        try:
            client = get_llm_client("classify")
            result = await client.chat(
                [LLMMessage(role="user", content=prompt)],
                max_tokens=64,
                temperature=0.1,
            )
            import json as _json
            text = (result.content or "").strip()
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            data = _json.loads(text)
            msg.classification = data.get("label", "other")
            msg.classification_confidence = float(data.get("confidence", 0.5))
        except Exception:
            msg.classification = "other"
            msg.classification_confidence = 0.0

        await db.commit()


@app.task(queue="default")
async def run_followup(campaign_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default")
async def run_reminders() -> None:
    raise NotImplementedError


@app.task(queue="enrichment", retry=procrastinate.RetryStrategy(max_attempts=2))
async def enrich_contact_task(contact_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.enrichment import enrich_contact

    async with AsyncSessionLocal() as db:
        await enrich_contact(contact_id=contact_id, db=db)


@app.periodic(cron="0 */6 * * *")
@app.task(queue="default")
async def cleanup_empty_contact_lists(timestamp: int) -> None:
    """Delete contact lists with 0 contacts that are older than 1 hour."""
    from sqlalchemy import delete, func, select
    from sqlalchemy.orm import aliased

    from app.core.database import AsyncSessionLocal
    from app.models.contact import Contact, ContactList

    cutoff = datetime.now(UTC) - timedelta(hours=1)
    async with AsyncSessionLocal() as db:
        subq = (
            select(Contact.list_id)
            .where(Contact.list_id.isnot(None))
            .group_by(Contact.list_id)
            .having(func.count() > 0)
        ).scalar_subquery()
        await db.execute(
            delete(ContactList).where(
                ContactList.created_at < cutoff,
                ContactList.id.not_in(subq),
            )
        )
        await db.commit()

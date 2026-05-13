import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.campaign import Campaign, CampaignMessage
from app.models.contact import Contact, ContactList
from app.models.inbox_message import InboxMessage
from app.models.reminder import Reminder
from app.models.smtp_account import SmtpAccount
from app.models.template import Template
from app.models.user import User


async def _patch_worker_session(monkeypatch, test_engine):
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", session_factory)


async def test_run_followup_enqueues_re_email(monkeypatch, test_engine, db_session):
    from app.workers import main as worker

    await _patch_worker_session(monkeypatch, test_engine)
    enqueued: list[str] = []

    async def fake_defer_async(**kwargs):
        enqueued.append(kwargs["message_id"])

    monkeypatch.setattr(worker.send_email, "defer_async", fake_defer_async)

    user = User(id=uuid.uuid4(), email="worker@test.com", password_hash="hash")
    contact_list = ContactList(id=uuid.uuid4(), user_id=user.id, name="List")
    contact = Contact(id=uuid.uuid4(), user_id=user.id, list_id=contact_list.id, email="lead@test.com")
    template = Template(id=uuid.uuid4(), user_id=user.id, name="Template", template_id="custom")
    smtp = SmtpAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="smtp",
        from_email="sender@test.com",
        from_name="Sender",
        is_active=True,
    )
    campaign = Campaign(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Campaign",
        list_id=contact_list.id,
        template_id=template.id,
        smtp_account_id=smtp.id,
    )
    original = CampaignMessage(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        contact_id=contact.id,
        subject="Original subject",
        body="Original body",
        status="sent",
        sent_at=datetime.now(UTC) - timedelta(days=4),
    )
    db_session.add_all([user, contact_list, contact, template, smtp, campaign, original])
    await db_session.commit()

    await worker.run_followup.func(str(campaign.id))

    rows = await db_session.execute(
        select(CampaignMessage).where(
            CampaignMessage.campaign_id == campaign.id,
            CampaignMessage.status == "pending",
        )
    )
    followups = rows.scalars().all()
    assert len(followups) == 1
    assert followups[0].subject == "Re: Original subject"
    assert enqueued == [str(followups[0].id)]


async def test_run_reminders_creates_inbox_notification(monkeypatch, test_engine, db_session):
    from app.workers import main as worker

    await _patch_worker_session(monkeypatch, test_engine)

    user = User(id=uuid.uuid4(), email="reminder@test.com", password_hash="hash")
    contact = Contact(id=uuid.uuid4(), user_id=user.id, email="lead@test.com", contact_name="Lead")
    smtp = SmtpAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="smtp",
        from_email="sender@test.com",
        from_name="Sender",
        is_active=True,
    )
    reminder = Reminder(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_id=contact.id,
        remind_at=datetime.now(UTC) - timedelta(minutes=1),
        action="Follow up",
        status="pending",
    )
    db_session.add_all([user, contact, smtp, reminder])
    await db_session.commit()

    await worker.run_reminders.func()

    await db_session.refresh(reminder)
    assert reminder.status == "sent"
    assert reminder.sent_at is not None

    rows = await db_session.execute(select(InboxMessage).where(InboxMessage.user_id == user.id))
    inbox = rows.scalar_one()
    assert inbox.message_id == f"reminder:{reminder.id}"
    assert inbox.body_text == "Follow up"


def test_lead_job_payload_data_supports_nested_and_flat_contracts():
    from app.workers.main import _lead_job_data

    flat = {
        "lead_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "title": "Flat title",
        "service_offered": "websites",
    }
    nested = {
        "lead_id": flat["lead_id"],
        "user_id": flat["user_id"],
        "title": "Legacy flat title",
        "data": {
            "title": "Nested title",
            "icp_description": "automation",
        },
    }

    assert _lead_job_data(flat) == {
        "title": "Flat title",
        "service_offered": "websites",
    }
    assert _lead_job_data(nested) == {
        "title": "Nested title",
        "icp_description": "automation",
    }

"""Procrastinate worker entry point. Task implementations live in app.services."""
import procrastinate

from app.core.config import settings

app = procrastinate.App(
    connector=procrastinate.PsycopgConnector(
        json_dumps=None,
        json_loads=None,
    )
)


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def generate_letters(campaign_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=3))
async def send_email(message_id: str) -> None:
    raise NotImplementedError


@app.task(queue="default")
async def poll_inbox() -> None:
    raise NotImplementedError


@app.task(queue="default", retry=procrastinate.RetryStrategy(max_attempts=2))
async def classify_inbox_message(inbox_message_id: str) -> None:
    raise NotImplementedError


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

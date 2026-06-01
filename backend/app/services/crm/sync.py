import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact

logger = logging.getLogger(__name__)


async def sync_to_crm(db: AsyncSession, contact_id: str, event: str, payload: dict | None = None):
    """
    Simulates sending data back to the CRM (amoCRM / Bitrix24).
    In a real app, this would use OAuth tokens to make API requests.
    """
    row = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = row.scalar_one_or_none()
    
    if not contact or not contact.raw:
        return
        
    source = contact.raw.get("source")
    if not source:
        return

    logger.info("[CRM SYNC] Sending event %r for contact %s to %s", event, contact_id, source.upper())
    
    # Mocking the sync based on CRM
    if source == "amocrm":
        # Normally we'd extract the lead_id from form_data and send an API request
        logger.info("[amoCRM Mock] -> Adding note: Event=%s, Payload=%s", event, payload)
        
    elif source == "bitrix24":
        logger.info("[Bitrix24 Mock] -> Sending comment to Lead: Event=%s, Payload=%s", event, payload)
        
    else:
        logger.warning("[CRM SYNC] Unknown source %r for contact %s", source, contact_id)

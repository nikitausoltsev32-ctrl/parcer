import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.contact import Contact

logger = logging.getLogger(__name__)

async def sync_to_crm(db: AsyncSession, contact_id: str, event: str, payload: dict = None):
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

    logger.info(f"[CRM SYNC] Sending event '{event}' for contact {contact_id} to {source.upper()}")
    
    # Mocking the sync based on CRM
    if source == "amocrm":
        form_data = contact.raw.get("form_data", {})
        # Normally we'd extract the lead_id from form_data and send an API request
        logger.info(f"[amoCRM Mock] -> Adding note: Event={event}, Payload={payload}")
        
    elif source == "bitrix24":
        bx_payload = contact.raw.get("payload", {})
        logger.info(f"[Bitrix24 Mock] -> Sending comment to Lead: Event={event}, Payload={payload}")
        
    else:
        logger.warning(f"[CRM SYNC] Unknown source '{source}' for contact {contact_id}")

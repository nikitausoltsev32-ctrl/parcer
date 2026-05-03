import uuid
from datetime import datetime

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    list_id: uuid.UUID
    template_id: uuid.UUID
    smtp_account_id: uuid.UUID
    send_rate_per_hour: int = 30


class CampaignRead(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    stats: dict
    list_id: uuid.UUID
    template_id: uuid.UUID
    smtp_account_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignMessageRead(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    subject: str
    body: str
    status: str
    sent_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}


class ContactListRead(BaseModel):
    id: uuid.UUID
    name: str
    source: str
    total_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateRead(BaseModel):
    id: uuid.UUID
    name: str
    template_id: str
    tone: str
    custom_instruction: str | None

    model_config = {"from_attributes": True}

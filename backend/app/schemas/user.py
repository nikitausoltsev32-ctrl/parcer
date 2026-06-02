import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


class BusinessProfile(BaseModel):
    business: str | None = None
    offer: str | None = None
    city: str | None = None
    website: str | None = None
    website_url: str | None = None
    icp: dict[str, Any] | None = None
    tone_default: str = "friendly"


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    email_verified_at: datetime | None
    business_profile: BusinessProfile | None
    plan: str
    leads_quota: int
    sends_quota: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    business_profile: BusinessProfile | None = None

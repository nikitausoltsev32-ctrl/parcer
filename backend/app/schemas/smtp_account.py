import uuid
from datetime import datetime

from pydantic import BaseModel


class SmtpAccountCreate(BaseModel):
    provider: str
    from_email: str
    from_name: str = ""
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    imap_host: str | None = None
    imap_port: int | None = None
    daily_limit: int = 30


class SmtpAccountRead(BaseModel):
    id: uuid.UUID
    provider: str
    from_email: str
    from_name: str
    host: str | None
    port: int | None
    username: str | None
    daily_limit: int
    is_active: bool
    last_verified_at: datetime | None
    oauth_connected: bool = False

    @classmethod
    def from_orm(cls, obj):
        data = {
            "id": obj.id,
            "provider": obj.provider,
            "from_email": obj.from_email,
            "from_name": obj.from_name,
            "host": obj.host,
            "port": obj.port,
            "username": obj.username,
            "daily_limit": obj.daily_limit,
            "is_active": obj.is_active,
            "last_verified_at": obj.last_verified_at,
            "oauth_connected": bool(obj.oauth_refresh_token),
        }
        return cls(**data)

    model_config = {"from_attributes": True}

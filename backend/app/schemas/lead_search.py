from typing import Any

from pydantic import BaseModel, Field


class LeadSearchCreate(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=5, ge=1, le=50)
    list_name: str | None = Field(default=None, max_length=120)
    fast_mode: bool = True
    ai_model: str | None = Field(default=None, max_length=120)


class LeadSearchRead(BaseModel):
    list_id: str
    list_name: str
    saved: int
    contacts: list[dict[str, Any]]
    log_id: str

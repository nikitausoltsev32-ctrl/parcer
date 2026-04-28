from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthToken(Base):
    __tablename__ = "token_store"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    purpose: Mapped[str] = mapped_column("prefix", String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

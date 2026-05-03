import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SmtpAccount(Base):
    __tablename__ = "smtp_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    from_email: Mapped[str] = mapped_column(String)
    from_name: Mapped[str] = mapped_column(String)
    host: Mapped[str | None] = mapped_column(String, nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    password_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    imap_host: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oauth_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    oauth_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=30)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

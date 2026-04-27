import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String)
    template_id: Mapped[str] = mapped_column(String)
    tone: Mapped[str] = mapped_column(String, default="friendly")
    language: Mapped[str] = mapped_column(String, default="ru")
    custom_instruction: Mapped[str | None] = mapped_column(String, nullable=True)

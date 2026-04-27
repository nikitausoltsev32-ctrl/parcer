"""CRM contact operations. Full implementation in Phase 4."""

from sqlalchemy.ext.asyncio import AsyncSession


async def set_status(db: AsyncSession, contact_id: str, status: str) -> None:
    raise NotImplementedError


async def add_note(db: AsyncSession, contact_id: str, text: str) -> None:
    raise NotImplementedError


async def set_next_step(db: AsyncSession, contact_id: str, action: str, at) -> None:
    raise NotImplementedError

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def store_token_for(db: AsyncSession, prefix: str, value: str, ttl_seconds: int) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    await db.execute(
        text(
            "INSERT INTO token_store (token, prefix, value, expires_at) "
            "VALUES (:token, :prefix, :value, :expires_at)"
        ),
        {"token": token, "prefix": prefix, "value": value, "expires_at": expires_at},
    )
    await db.commit()
    return token


async def consume_token(db: AsyncSession, prefix: str, token: str) -> str | None:
    now = datetime.now(UTC)
    result = await db.execute(
        select(text("value")).select_from(text("token_store")).where(
            text("token = :token AND prefix = :prefix AND expires_at > :now")
        ).bindparams(token=token, prefix=prefix, now=now)
    )
    row = result.first()
    if not row:
        return None
    await db.execute(
        text("DELETE FROM token_store WHERE token = :token"),
        {"token": token},
    )
    await db.commit()
    return row[0]


async def purge_expired_tokens(db: AsyncSession) -> None:
    await db.execute(
        text("DELETE FROM token_store WHERE expires_at <= :now"),
        {"now": datetime.now(UTC)},
    )
    await db.commit()

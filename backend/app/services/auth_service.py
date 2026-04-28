import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import send_reset_password_email, send_verify_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.core.tokens import consume_token, store_token_for
from app.models.user import User

VERIFY_TTL = 86400
RESET_TTL = 3600
REFRESH_MAX_AGE = 604800


async def register_user(
    db: AsyncSession, email: str, password: str, full_name: str | None, llm_consent: bool = False
) -> User:
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        id=uuid.uuid4(),
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        llm_consent_at=datetime.now(UTC) if llm_consent else None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = await store_token_for(db, "verify_email", str(user.id), VERIFY_TTL)
    send_verify_email(user.email, token)
    return user


async def verify_user_email(db: AsyncSession, token: str) -> None:
    user_id = await consume_token(db, "verify_email", token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email_verified_at = datetime.now(UTC)
    await db.commit()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> tuple[str, str]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token({"sub": str(user.id)})
    return access, refresh


def refresh_access(refresh_token: str | None) -> tuple[str, str]:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    payload = decode_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    return create_access_token({"sub": user_id}), create_refresh_token({"sub": user_id})


async def request_password_reset(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if user:
        token = await store_token_for(db, "reset_password", str(user.id), RESET_TTL)
        send_reset_password_email(user.email, token)


async def reset_user_password(db: AsyncSession, token: str, new_password: str) -> None:
    user_id = await consume_token(db, "reset_password", token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(new_password)
    await db.commit()

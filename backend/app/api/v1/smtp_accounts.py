import asyncio
import smtplib
import ssl
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.fernet import decrypt_password, encrypt_password
from app.models.smtp_account import SmtpAccount
from app.models.user import User
from app.schemas.smtp_account import SmtpAccountCreate, SmtpAccountRead

router = APIRouter(prefix="/smtp-accounts", tags=["smtp"])

PROVIDER_DEFAULTS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587, "imap_host": "imap.gmail.com", "imap_port": 993},
    "yandex": {"host": "smtp.yandex.ru", "port": 465, "imap_host": "imap.yandex.ru", "imap_port": 993},
    "mailru": {"host": "smtp.mail.ru", "port": 465, "imap_host": "imap.mail.ru", "imap_port": 993},
    "outlook": {"host": "smtp.office365.com", "port": 587, "imap_host": "outlook.office365.com", "imap_port": 993},
}


def _try_send(host: str, port: int, username: str, password: str) -> None:
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=10) as s:
            s.login(username, password)
    else:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.login(username, password)


def _default_sender_name(email: str, from_name: str | None) -> str:
    clean_name = (from_name or "").strip()
    if clean_name:
        return clean_name
    return email.split("@", 1)[0].strip() or email


@router.get("", response_model=list[SmtpAccountRead])
async def list_smtp(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(SmtpAccount).where(SmtpAccount.user_id == user.id))
    accounts = rows.scalars().all()
    return [SmtpAccountRead.from_orm(a) for a in accounts]


@router.post("", response_model=SmtpAccountRead, status_code=201)
async def create_smtp(
    body: SmtpAccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = body.provider.strip().lower()
    from_email = body.from_email.strip()
    defaults = PROVIDER_DEFAULTS.get(provider, {})
    host = body.host or defaults.get("host")
    port = body.port or defaults.get("port")
    username = body.username or from_email
    imap_host = body.imap_host or defaults.get("imap_host")
    imap_port = body.imap_port or defaults.get("imap_port")

    if not body.password:
        raise HTTPException(status_code=400, detail="Пароль приложения обязателен для SMTP-подключения")
    if not host or not port:
        raise HTTPException(status_code=400, detail="SMTP-хост и порт обязательны для этого провайдера")

    account = SmtpAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        provider=provider,
        from_email=from_email,
        from_name=_default_sender_name(from_email, body.from_name),
        host=host,
        port=port,
        username=username,
        password_encrypted=encrypt_password(body.password) if body.password else None,
        imap_host=imap_host,
        imap_port=imap_port,
        daily_limit=body.daily_limit,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return SmtpAccountRead.from_orm(account)


@router.post("/{smtp_id}/verify", response_model=SmtpAccountRead)
async def verify_smtp(
    smtp_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(SmtpAccount).where(SmtpAccount.id == smtp_id, SmtpAccount.user_id == user.id)
    )
    account = row.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        if account.oauth_refresh_token:
            from app.services.gmail import get_valid_access_token
            await get_valid_access_token(account, db)
        else:
            if not account.host or not account.port or not account.username or not account.password_encrypted:
                raise ValueError("SMTP account is incomplete")
            password = decrypt_password(account.password_encrypted)
            await asyncio.to_thread(
                _try_send, account.host, account.port, account.username, password
            )
        account.last_verified_at = datetime.now(UTC)
        account.is_active = True
    except Exception as e:
        account.is_active = False
        await db.commit()
        raise HTTPException(status_code=400, detail=f"Ошибка подключения: {e}")

    await db.commit()
    await db.refresh(account)
    return SmtpAccountRead.from_orm(account)


@router.delete("/{smtp_id}", status_code=204)
async def delete_smtp(
    smtp_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(SmtpAccount).where(SmtpAccount.id == smtp_id, SmtpAccount.user_id == user.id)
    )
    account = row.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(account)
    await db.commit()


# ── Gmail OAuth ────────────────────────────────────────────────────────────────

@router.get("/gmail/oauth/start")
async def gmail_oauth_start(user: User = Depends(get_current_user)):
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth не настроен (GOOGLE_CLIENT_ID не задан)")
    from app.services.gmail import get_auth_url, make_state
    state = make_state(str(user.id))
    return {"auth_url": get_auth_url(state)}


@router.get("/gmail/oauth/callback")
async def gmail_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    frontend = settings.frontend_url
    if error or not code or not state:
        return RedirectResponse(f"{frontend}/app/smtp?gmail_error=1")

    from app.services.gmail import exchange_code, verify_state
    user_id = verify_state(state)
    if not user_id:
        return RedirectResponse(f"{frontend}/app/smtp?gmail_error=2")

    try:
        info = await exchange_code(code)
    except Exception:
        return RedirectResponse(f"{frontend}/app/smtp?gmail_error=3")

    row = await db.execute(
        select(SmtpAccount).where(
            SmtpAccount.user_id == uuid.UUID(user_id),
            SmtpAccount.provider == "gmail",
            SmtpAccount.from_email == info["email"],
        )
    )
    account = row.scalar_one_or_none()

    if account:
        account.oauth_refresh_token = info["refresh_token"] or account.oauth_refresh_token
        account.oauth_access_token = info["access_token"]
        from datetime import timedelta
        account.oauth_expires_at = datetime.now(UTC) + timedelta(seconds=info["expires_in"] - 60)
        account.is_active = True
    else:
        account = SmtpAccount(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            provider="gmail",
            from_email=info["email"],
            from_name=info["name"],
            oauth_refresh_token=info["refresh_token"],
            oauth_access_token=info["access_token"],
            is_active=True,
        )
        from datetime import timedelta
        account.oauth_expires_at = datetime.now(UTC) + timedelta(seconds=info["expires_in"] - 60)
        db.add(account)

    await db.commit()
    return RedirectResponse(f"{frontend}/app/smtp?gmail_connected=1")

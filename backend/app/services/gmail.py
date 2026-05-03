"""Gmail OAuth 2.0 + Gmail API helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import time
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"

SCOPES = " ".join([
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
])


# ── State signing ──────────────────────────────────────────────────────────────

def make_state(user_id: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"uid": user_id, "ts": int(time.time())}).encode()
    ).decode().rstrip("=")
    sig = _hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{sig}"


def verify_state(state: str) -> str | None:
    try:
        payload, sig = state.rsplit(".", 1)
        expected = _hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not _hmac.compare_digest(sig, expected):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        if int(time.time()) - data["ts"] > 600:
            return None
        return data["uid"]
    except Exception:
        return None


# ── OAuth flow ─────────────────────────────────────────────────────────────────

def get_auth_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(_TOKEN_URL, data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        })
        r.raise_for_status()
        tokens = r.json()

        ui = await client.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        ui.raise_for_status()
        userinfo = ui.json()

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_in": tokens.get("expires_in", 3600),
        "email": userinfo.get("email", ""),
        "name": userinfo.get("name", ""),
    }


# ── Token management ───────────────────────────────────────────────────────────

async def get_valid_access_token(account, db: AsyncSession) -> str:
    now = datetime.now(UTC)
    if account.oauth_access_token and account.oauth_expires_at and account.oauth_expires_at > now:
        return account.oauth_access_token

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(_TOKEN_URL, data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": account.oauth_refresh_token,
            "grant_type": "refresh_token",
        })
        r.raise_for_status()
        data = r.json()

    account.oauth_access_token = data["access_token"]
    account.oauth_expires_at = now + timedelta(seconds=data.get("expires_in", 3600) - 60)
    await db.commit()
    return account.oauth_access_token


# ── Sending ────────────────────────────────────────────────────────────────────

async def send_message(account, to_email: str, subject: str, body: str, db: AsyncSession, *, unsub_url: str | None = None) -> None:
    token = await get_valid_access_token(account, db)
    mime = MIMEMultipart("alternative")
    mime["Subject"] = subject
    mime["From"] = f"{account.from_name} <{account.from_email}>"
    mime["To"] = to_email
    if unsub_url:
        mime["List-Unsubscribe"] = f"<{unsub_url}>"
        mime["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    mime.attach(MIMEText(body, "plain", "utf-8"))
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode().rstrip("=")

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{_GMAIL}/messages/send",
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw},
        )
        r.raise_for_status()


# ── Inbox polling ──────────────────────────────────────────────────────────────

async def list_unread_messages(account, db: AsyncSession, max_results: int = 20) -> list[dict]:
    import asyncio
    token = await get_valid_access_token(account, db)

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{_GMAIL}/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"labelIds": "INBOX", "q": "is:unread", "maxResults": max_results},
        )
        r.raise_for_status()
        ids = [m["id"] for m in r.json().get("messages", [])]

    results = await asyncio.gather(
        *[_fetch_message_metadata(mid, token) for mid in ids],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, dict)]


async def _fetch_message_metadata(msg_id: str, token: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
        )
        r.raise_for_status()
        data = r.json()

    headers = {h["name"].lower(): h["value"] for h in data.get("payload", {}).get("headers", [])}
    return {
        "gmail_id": msg_id,
        "from_email": _parse_email_addr(headers.get("from", "")),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": data.get("snippet", ""),
    }


def _parse_email_addr(header: str) -> str:
    if "<" in header and ">" in header:
        return header.split("<")[1].split(">")[0].strip()
    return header.strip()

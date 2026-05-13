from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_access_token


def user_or_ip_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        payload = decode_access_token(auth[7:])
        user_id = payload.get("sub") if payload else None
        if user_id:
            return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_remote_address)

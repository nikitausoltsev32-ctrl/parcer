import hashlib
import hmac

from app.core.config import settings


def sign(tracking_id: str) -> str:
    return hmac.new(
        settings.tracking_secret.encode(),
        tracking_id.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]


def verify(tracking_id: str, sig: str) -> bool:
    return hmac.compare_digest(sign(tracking_id), sig)


def open_url(tracking_id: str) -> str:
    sig = sign(tracking_id)
    return f"{settings.base_url}/api/v1/t/open/{tracking_id}?sig={sig}"


def click_url(tracking_id: str, destination: str) -> str:
    from urllib.parse import quote
    sig = sign(tracking_id)
    return f"{settings.base_url}/api/v1/t/click/{tracking_id}?sig={sig}&url={quote(destination, safe='')}"


def unsub_url(tracking_id: str) -> str:
    sig = sign(tracking_id)
    return f"{settings.base_url}/api/v1/t/unsub/{tracking_id}?sig={sig}"

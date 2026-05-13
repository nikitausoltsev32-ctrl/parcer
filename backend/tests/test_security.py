from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify():
    h = hash_password("mysecret")
    assert verify_password("mysecret", h) is True
    assert verify_password("wrong", h) is False


def test_verify_password_returns_false_for_invalid_stored_hash():
    assert verify_password("mysecret", "legacy-or-corrupt-hash") is False


def test_token_roundtrip():
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"


def test_invalid_token_returns_none():
    assert decode_access_token("not.a.valid.token") is None

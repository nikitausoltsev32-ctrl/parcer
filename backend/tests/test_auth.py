
from sqlalchemy import select

from app.models.auth_token import AuthToken
from app.models.user import User


async def test_register_success(client):
    r = await client.post("/api/v1/auth/register", json={"email": "a@test.com", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["email"] == "a@test.com"


async def test_register_duplicate(client):
    payload = {"email": "dup@test.com", "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


async def test_register_short_password(client):
    r = await client.post("/api/v1/auth/register", json={"email": "b@test.com", "password": "123"})
    assert r.status_code == 422


async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={"email": "c@test.com", "password": "password123"})
    r = await client.post("/api/v1/auth/login", json={"email": "c@test.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "d@test.com", "password": "password123"})
    r = await client.post("/api/v1/auth/login", json={"email": "d@test.com", "password": "wrong"})
    assert r.status_code == 401


async def test_login_with_invalid_stored_hash_returns_401(client, db_session):
    db_session.add(User(email="legacy@test.com", password_hash="legacy-or-corrupt-hash"))
    await db_session.commit()

    r = await client.post("/api/v1/auth/login", json={"email": "legacy@test.com", "password": "password123"})

    assert r.status_code == 401


async def test_get_me_with_token(client):
    await client.post("/api/v1/auth/register", json={"email": "e@test.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": "e@test.com", "password": "password123"})
    token = login.json()["access_token"]
    r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "e@test.com"


async def test_get_me_no_auth(client):
    r = await client.get("/api/v1/me")
    assert r.status_code in (401, 403)


async def test_logout(client):
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204


async def test_register_stores_verify_token_in_database(client, db_session):
    await client.post("/api/v1/auth/register", json={"email": "verify@test.com", "password": "password123"})

    result = await db_session.execute(select(AuthToken).where(AuthToken.purpose == "verify_email"))
    token = result.scalar_one()

    assert token.token
    assert token.expires_at is not None


async def test_verify_email_consumes_database_token(client, db_session):
    await client.post("/api/v1/auth/register", json={"email": "verify2@test.com", "password": "password123"})
    token = (
        await db_session.execute(select(AuthToken).where(AuthToken.purpose == "verify_email"))
    ).scalar_one()

    response = await client.post(f"/api/v1/auth/verify-email?token={token.token}")

    assert response.status_code == 200
    user = (
        await db_session.execute(select(User).where(User.email == "verify2@test.com"))
    ).scalar_one()
    assert user.email_verified_at is not None
    consumed = (
        await db_session.execute(select(AuthToken).where(AuthToken.token == token.token))
    ).scalar_one_or_none()
    assert consumed is None


async def test_reset_password_uses_database_token(client, db_session):
    await client.post("/api/v1/auth/register", json={"email": "reset@test.com", "password": "password123"})
    await client.post("/api/v1/auth/forgot-password", json={"email": "reset@test.com"})
    token = (
        await db_session.execute(select(AuthToken).where(AuthToken.purpose == "reset_password"))
    ).scalar_one()

    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token.token, "new_password": "newpassword123"},
    )
    login = await client.post("/api/v1/auth/login", json={"email": "reset@test.com", "password": "newpassword123"})

    assert reset.status_code == 200
    assert login.status_code == 200

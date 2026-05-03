from cryptography.fernet import Fernet


async def _auth_headers(client, email: str) -> dict[str, str]:
    payload = {"email": email, "password": "password123"}
    await client.post("/api/v1/auth/register", json=payload)
    login = await client.post("/api/v1/auth/login", json=payload)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_yandex_smtp_uses_server_defaults(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.fernet_key", Fernet.generate_key().decode())
    headers = await _auth_headers(client, "smtp-yandex@test.com")

    response = await client.post(
        "/api/v1/smtp-accounts",
        headers=headers,
        json={
            "provider": "yandex",
            "from_email": "sender@yandex.ru",
            "from_name": "",
            "password": "app-password",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["host"] == "smtp.yandex.ru"
    assert data["port"] == 465
    assert data["username"] == "sender@yandex.ru"
    assert data["from_name"] == "sender"


async def test_create_mailru_smtp_uses_server_defaults(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.fernet_key", Fernet.generate_key().decode())
    headers = await _auth_headers(client, "smtp-mailru@test.com")

    response = await client.post(
        "/api/v1/smtp-accounts",
        headers=headers,
        json={
            "provider": "mailru",
            "from_email": "lead@bk.ru",
            "from_name": "Lead Sender",
            "password": "app-password",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["host"] == "smtp.mail.ru"
    assert data["port"] == 465
    assert data["username"] == "lead@bk.ru"
    assert data["from_name"] == "Lead Sender"


async def test_create_custom_smtp_requires_manual_connection_details(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.fernet_key", Fernet.generate_key().decode())
    headers = await _auth_headers(client, "smtp-custom@test.com")

    response = await client.post(
        "/api/v1/smtp-accounts",
        headers=headers,
        json={
            "provider": "custom",
            "from_email": "sender@example.com",
            "from_name": "Sender",
            "password": "app-password",
        },
    )

    assert response.status_code == 400
    assert "SMTP" in response.json()["detail"]

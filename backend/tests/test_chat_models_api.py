async def _auth_headers(client, email: str = "chat-models@test.com") -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_get_chat_models_returns_nvidia_models_when_configured(monkeypatch, client):
    monkeypatch.setattr("app.core.config.settings.nvidia_api_key", "test-nvidia-key")

    headers = await _auth_headers(client)
    response = await client.get("/api/v1/chat/models", headers=headers)

    assert response.status_code == 200
    assert response.json() == [
        {"id": "nvidia/z-ai/glm-5.1", "label": "GLM 5.1", "sub": "NVIDIA"},
        {
            "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            "label": "Nemotron 3 Nano Omni 30B",
            "sub": "NVIDIA reasoning",
        },
    ]


async def test_get_chat_models_returns_empty_list_when_not_configured(monkeypatch, client):
    monkeypatch.setattr("app.core.config.settings.nvidia_api_key", "")

    headers = await _auth_headers(client, email="chat-models-empty@test.com")
    response = await client.get("/api/v1/chat/models", headers=headers)

    assert response.status_code == 200
    assert response.json() == []

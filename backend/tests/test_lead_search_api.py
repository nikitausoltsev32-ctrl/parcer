async def _auth_headers(client, email: str = "lead-api@test.com") -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_post_lead_search_creates_saved_search(monkeypatch, client):
    async def fake_run_lead_search(db, *, user, query, city, limit, list_name=None):
        from app.services.leads.pipeline import LeadSearchResult

        return LeadSearchResult(
            list_id="00000000-0000-0000-0000-000000000001",
            list_name=list_name or "Search",
            saved=1,
            leads=[{"name": "Studio One", "website": "https://studio.test", "score": 80}],
            log_id="00000000-0000-0000-0000-000000000002",
        )

    monkeypatch.setattr("app.api.v1.lead_search.run_lead_search", fake_run_lead_search)
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/lead-search",
        headers=headers,
        json={"query": "design studios", "city": "Kazan", "limit": 10, "list_name": "Kazan design"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["saved"] == 1
    assert data["list_name"] == "Kazan design"
    assert data["contacts"][0]["name"] == "Studio One"

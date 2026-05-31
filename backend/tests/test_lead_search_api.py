import asyncio
import uuid


async def _auth_headers(client, email: str = "lead-api@test.com") -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_post_lead_search_creates_pending_search_log(monkeypatch, client, db_session):
    from sqlalchemy import select

    from app.models.lead_processing_log import LeadProcessingLog

    real_create_task = asyncio.create_task

    async def noop():
        return None

    def fake_create_task(coro):
        coro.close()
        return real_create_task(noop())

    monkeypatch.setattr("app.services.leads.async_search.asyncio.create_task", fake_create_task)
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/lead-search",
        headers=headers,
        json={"query": "design studios", "city": "Kazan", "limit": 10, "list_name": "Kazan design"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["log_id"]

    log = (
        await db_session.execute(select(LeadProcessingLog).where(LeadProcessingLog.id == uuid.UUID(data["log_id"])))
    ).scalar_one()
    assert log.outcome == "pending"
    assert log.search_query_original == "design studios"
    assert log.meta["city"] == "Kazan"
    assert log.meta["progress"]["stage"] == "queued"
    assert log.meta["progress"]["target"] == 10
    event = log.meta["events"][0]
    assert event["stage"] == "queued"
    assert event["status"] == "queued"
    assert event["actor"] == "LeadSearchJob"
    assert event["api"] == "Supabase"
    assert event["tool"] == "lead_search"
    assert event["label"] == log.meta["progress"]["label"]
    assert event["metrics"]["target"] == 10


async def test_post_lead_search_caps_target_by_user_quota(monkeypatch, client, db_session):
    from sqlalchemy import select

    from app.models.lead_processing_log import LeadProcessingLog
    from app.models.user import User

    real_create_task = asyncio.create_task

    async def noop():
        return None

    def fake_create_task(coro):
        coro.close()
        return real_create_task(noop())

    monkeypatch.setattr("app.services.leads.async_search.asyncio.create_task", fake_create_task)
    headers = await _auth_headers(client, email="lead-quota-api@test.com")
    user = (await db_session.execute(select(User).where(User.email == "lead-quota-api@test.com"))).scalar_one()
    user.leads_quota = 3
    await db_session.commit()

    response = await client.post(
        "/api/v1/lead-search",
        headers=headers,
        json={"query": "design studios", "city": "Kazan", "limit": 10, "fast_mode": False},
    )

    assert response.status_code == 202
    data = response.json()

    log = (
        await db_session.execute(select(LeadProcessingLog).where(LeadProcessingLog.id == uuid.UUID(data["log_id"])))
    ).scalar_one()
    assert log.meta["requested_limit"] == 10
    assert log.meta["limit"] == 3
    assert log.meta["progress"]["target"] == 3


async def test_post_lead_search_rejects_when_user_has_no_leads_quota(monkeypatch, client, db_session):
    from sqlalchemy import select

    from app.models.lead_processing_log import LeadProcessingLog
    from app.models.user import User

    real_create_task = asyncio.create_task

    async def noop():
        return None

    def fake_create_task(coro):
        coro.close()
        return real_create_task(noop())

    monkeypatch.setattr("app.services.leads.async_search.asyncio.create_task", fake_create_task)
    headers = await _auth_headers(client, email="lead-zero-quota-api@test.com")
    user = (await db_session.execute(select(User).where(User.email == "lead-zero-quota-api@test.com"))).scalar_one()
    user.leads_quota = 0
    await db_session.commit()

    response = await client.post(
        "/api/v1/lead-search",
        headers=headers,
        json={"query": "design studios", "city": "Kazan", "limit": 10, "fast_mode": False},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "lead_quota_exhausted"

    logs = (await db_session.execute(select(LeadProcessingLog))).scalars().all()
    assert logs == []


async def test_get_lead_search_status_returns_serialized_leads(client, db_session):
    from sqlalchemy import select

    from app.models.lead import Lead, LeadList
    from app.models.lead_processing_log import LeadProcessingLog
    from app.models.user import User

    headers = await _auth_headers(client, email="lead-status@test.com")
    user = (await db_session.execute(select(User).where(User.email == "lead-status@test.com"))).scalar_one()

    lead_list = LeadList(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Kazan design",
        source="search",
        total_count=1,
    )
    lead = Lead(
        id=uuid.uuid4(),
        user_id=user.id,
        list_id=lead_list.id,
        domain="studio.test",
        website="https://studio.test",
        company_name="Studio One",
        city="Kazan",
        description="Studio One designs B2B websites.",
        lead_fit={"score": 82, "priority": "high", "reason": "Strong website fit"},
        reason_to_contact="На сайте есть портфолио B2B проектов.",
        processing={"ai_level": "light", "source": "serp_google", "url_label": "company_homepage"},
    )
    log = LeadProcessingLog(
        id=uuid.uuid4(),
        user_id=user.id,
        search_query_original="design studios",
        outcome="success",
        meta={
            "lead_list_id": str(lead_list.id),
            "list_name": lead_list.name,
            "saved_leads": 1,
            "events": [
                {
                    "ts": "2026-05-13T00:00:00+00:00",
                    "stage": "save",
                    "message": "Saved lead",
                    "domain": "studio.test",
                    "status": "completed",
                    "label": "Saved lead",
                    "api": "Supabase",
                    "actor": "SaveAgent",
                    "tool": "lead_storage",
                    "metrics": {"saved": 1, "target": 1},
                }
            ],
        },
    )
    db_session.add_all([lead_list, lead, log])
    await db_session.commit()

    response = await client.get(f"/api/v1/lead-search/{log.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["list_id"] == str(lead_list.id)
    assert data["saved"] == 1
    assert data["progress"]["stage"] == "done"
    assert data["progress"]["saved"] == 1
    assert data["leads"][0]["name"] == "Studio One"
    assert data["leads"][0]["description"] == "Studio One designs B2B websites."
    assert data["leads"][0]["score"] == 82
    assert data["events"] == log.meta["events"]
    assert data["leads"][0]["reason_to_contact"] == "На сайте есть портфолио B2B проектов."

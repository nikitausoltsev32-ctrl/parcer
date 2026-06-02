import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.campaign import CampaignMessage
from app.models.contact import Contact
from app.models.lead import Lead, LeadList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
from app.services.leads.light_ai import LightAIResult
from app.services.leads.pipeline import run_lead_search


async def test_run_lead_search_saves_contact_list_contacts_and_log(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="lead@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Studio One",
                "website": "https://studio.test",
                "email": None,
                "phone": "+7 999 000-00-00",
                "city": city,
                "industry": "Design",
                "address": "Baumana 1",
                "source": "serp_google",
                "website_summary": "B2B website studio. Email hello@studio.test",
            },
            {
                "name": "Studio One duplicate",
                "website": "https://studio.test/about",
                "email": "other@studio.test",
                "phone": None,
                "city": city,
                "source": "serp_google",
            },
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=10,
        list_name="Design Kazan",
    )

    assert result.saved == 1
    assert result.list_name == "Design Kazan"
    assert result.contacts[0]["email"] == "hello@studio.test"
    assert result.contacts[0]["phone"] == "+7 999 000-00-00"
    assert result.contacts[0]["score"] >= 80

    lead_list = (await db_session.execute(select(LeadList))).scalar_one()
    lead = (await db_session.execute(select(Lead))).scalar_one()
    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()

    assert lead_list.source == "search"
    assert lead.domain == "studio.test"
    assert lead.lead_fit["score"] == result.contacts[0]["score"]
    assert log.urls_found == 2
    assert log.urls_after_filter == 1
    assert log.meta["saved_leads"] == 1
    assert log.meta["progress"]["stage"] == "partial"
    assert log.meta["progress"]["saved"] == 1
    event_stages = {e["stage"] for e in log.meta.get("events", [])}
    assert "partial" in event_stages


async def test_run_lead_search_fast_mode_fetches_extra_candidates_without_capping_target(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="fast@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    limits_seen: list[int] = []

    async def fake_search_companies(query: str, city: str | None, limit: int):
        limits_seen.append(limit)
        return [
            {
                "name": f"Clinic {idx}",
                "website": f"https://clinic-{idx}.test",
                "phone": "+7 343 222-33-44",
                "city": city,
                "source": "serp_maps",
                "website_summary": "Dental clinic website.",
            }
            for idx in range(12)
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query, f"{query} companies", f"{query} contacts"]

    async def fake_crawl_website(website: str, plan: str):
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="dentistry",
        city="Ekaterinburg",
        limit=20,
        fast_mode=True,
    )

    assert result.saved == 12
    assert limits_seen == [50, 50]


async def test_run_lead_search_respects_user_leads_quota(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="quota@test.com", password_hash="hash", leads_quota=2)
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": f"Studio {idx}",
                "website": f"https://studio-{idx}.test",
                "phone": "+7 999 000-00-00",
                "city": city,
                "source": "serp_google",
                "website_summary": "B2B website studio.",
            }
            for idx in range(5)
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=10,
        fast_mode=False,
    )

    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()

    assert result.saved == 2
    assert log.meta["limit"] == 2
    assert log.meta["requested_limit"] == 10
    assert log.meta["progress"]["target"] == 2


async def test_run_lead_search_returns_empty_result_when_quota_is_zero(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="quota-zero@test.com", password_hash="hash", leads_quota=0)
    db_session.add(user)
    await db_session.commit()

    search_called = False

    async def fake_search_companies(query: str, city: str | None, limit: int):
        nonlocal search_called
        search_called = True
        return []

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=10,
        list_name="Quota zero",
    )

    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()
    lead_list = (await db_session.execute(select(LeadList))).scalar_one()

    assert search_called is False
    assert result.saved == 0
    assert result.leads == []
    assert lead_list.total_count == 0
    assert log.urls_found == 0
    assert log.urls_after_filter == 0
    assert log.meta["limit"] == 0
    assert log.meta["saved_leads"] == 0
    assert log.meta["quota_blocked"] is True
    assert log.meta["progress"]["target"] == 0
    assert log.meta["progress"]["stage"] == "partial"


async def test_run_lead_search_uses_extracted_description_without_deep_ai(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="fallback@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Fallback Studio",
                "website": "https://fallback.test",
                "email": None,
                "phone": None,
                "city": city,
                "industry": "Design",
                "source": "serp_google",
                "website_summary": "Raw search snippet should be lower priority.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return [
            {
                "url": "https://fallback.test/",
                "html": """
                <html>
                  <head><meta name="description" content="Meta summary from the website."></head>
                  <body><h1>Fallback Studio</h1><p>Website paragraph.</p></body>
                </html>
                """,
            }
        ]

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=1,
    )

    lead = (await db_session.execute(select(Lead))).scalar_one()

    assert lead.description == "Meta summary from the website."
    assert result.contacts[0]["description"] == "Meta summary from the website."
    assert result.contacts[0]["ai_level"] == "basic"
    assert result.contacts[0]["confidence"] == 0.3


async def test_run_lead_search_prefers_light_ai_description_from_about_section(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="light-desc@test.com", password_hash="hash", ai_credits_balance=3)
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Prom Tech",
                "website": "https://prom-tech.test",
                "email": None,
                "phone": None,
                "city": city,
                "industry": "Automation",
                "source": "serp_google",
                "website_summary": "Raw search snippet should be lower priority than AI description.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return [
            {
                "url": "https://prom-tech.test/",
                "html": """
                <html>
                  <head><meta name="description" content="Meta summary should be lower priority."></head>
                  <body>
                    <h1>Prom Tech</h1>
                    <section>
                      <h2>О компании</h2>
                      <p>Prom Tech designs industrial automation systems for plants.</p>
                    </section>
                  </body>
                </html>
                """,
            }
        ]

    async def fake_run_light_ai(**kwargs):
        assert kwargs["about_text"].startswith("О компании Prom Tech designs industrial automation")
        return LightAIResult(
            industry="Automation",
            city=kwargs["city"] or "",
            description="Prom Tech designs industrial automation systems for plants.",
            is_commercial=True,
            is_relevant_to_icp=True,
            relevance_score=59,
            pass_to_deep_ai=False,
            raw={},
        )

    async def fake_check_and_deduct(db, user_id: str, operation: str):
        assert operation == "light_ai_analysis"
        return 2

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)
    monkeypatch.setattr("app.services.leads.pipeline.run_light_ai", fake_run_light_ai)
    monkeypatch.setattr("app.services.leads.pipeline.check_and_deduct", fake_check_and_deduct)

    result = await run_lead_search(
        db_session,
        user=user,
        query="automation",
        city="Ekaterinburg",
        limit=1,
    )

    lead = (await db_session.execute(select(Lead))).scalar_one()

    assert lead.description == "Prom Tech designs industrial automation systems for plants."
    assert result.contacts[0]["description"] == "Prom Tech designs industrial automation systems for plants."
    assert result.contacts[0]["ai_level"] == "light"


async def test_run_lead_search_disables_deep_ai_for_trial_plan(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="trial-deep@test.com", password_hash="hash", plan="trial", ai_credits_balance=20)
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Trial Clinic",
                "website": "https://trial-clinic.test",
                "city": city,
                "source": "serp_google",
                "website_summary": "Private clinic website.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return [
            {
                "url": "https://trial-clinic.test/",
                "html": "<html><head><title>Trial Clinic</title></head><body><h1>Trial Clinic</h1></body></html>",
            }
        ]

    async def fake_run_light_ai(**kwargs):
        return LightAIResult(
            industry="Healthcare",
            city=kwargs["city"] or "",
            description="Trial Clinic provides private outpatient care.",
            hook="Есть коммерческие услуги.",
            is_commercial=True,
            is_relevant_to_icp=True,
            relevance_score=88,
            pass_to_deep_ai=True,
            raw={},
        )

    deep_ai_called = False

    async def fake_run_deep_ai(**kwargs):
        nonlocal deep_ai_called
        deep_ai_called = True
        return {"company_name": "Should not run"}

    async def fake_check_and_deduct(db, user_id: str, operation: str):
        return 1

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)
    monkeypatch.setattr("app.services.leads.pipeline.run_light_ai", fake_run_light_ai)
    monkeypatch.setattr("app.services.leads.pipeline.run_deep_ai", fake_run_deep_ai)
    monkeypatch.setattr("app.services.leads.pipeline.check_and_deduct", fake_check_and_deduct)

    result = await run_lead_search(
        db_session,
        user=user,
        query="private clinics",
        city="Ekaterinburg",
        limit=1,
    )

    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()

    assert deep_ai_called is False
    assert result.contacts[0]["ai_level"] == "light"
    assert log.meta["deep_ai_allowed"] is False
    assert all(entry["stage"] != "deep_ai" for entry in log.llm_calls or [])


async def test_run_lead_search_sends_raw_summary_to_light_ai_without_crawl(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="light-raw@test.com", password_hash="hash", ai_credits_balance=3)
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Smile Clinic",
                "website": "https://smile.test",
                "city": city,
                "source": "serp_google",
                "website_summary": "Smile Clinic treats adults and children in Ekaterinburg.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return []

    async def fake_run_light_ai(**kwargs):
        assert kwargs["meta_description"] == "Smile Clinic treats adults and children in Ekaterinburg."
        assert kwargs["visible_text_snippet"] == "Smile Clinic treats adults and children in Ekaterinburg."
        return LightAIResult(
            industry="Dentistry",
            city=kwargs["city"] or "",
            description="Smile Clinic treats adults and children in Ekaterinburg.",
            hook=None,
            is_commercial=True,
            is_relevant_to_icp=True,
            relevance_score=61,
            pass_to_deep_ai=False,
            raw={},
        )

    async def fake_check_and_deduct(db, user_id: str, operation: str):
        assert operation == "light_ai_analysis"
        return 2

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)
    monkeypatch.setattr("app.services.leads.pipeline.run_light_ai", fake_run_light_ai)
    monkeypatch.setattr("app.services.leads.pipeline.check_and_deduct", fake_check_and_deduct)

    result = await run_lead_search(
        db_session,
        user=user,
        query="стоматологии",
        city="Екатеринбург",
        limit=1,
    )

    lead = (await db_session.execute(select(Lead))).scalar_one()

    assert lead.description == "Smile Clinic treats adults and children in Ekaterinburg."
    assert lead.reason_to_contact is None
    assert result.contacts[0]["description"] == "Smile Clinic treats adults and children in Ekaterinburg."
    assert result.contacts[0]["reason_to_contact"] is None


async def test_run_lead_search_classifies_only_border_urls(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="classifier@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {"name": "Root Co", "website": "https://root.test", "source": "serp_google"},
            {"name": "Contact Co", "website": "https://contact.test/contacts", "source": "serp_google"},
            {"name": "Border Co", "website": "https://border.test/company/profile/123", "source": "serp_google"},
            {"name": "Article Co", "website": "https://article.test/company/profile/123", "source": "serp_google"},
            {"name": "Blocked Co", "website": "https://2gis.ru/kazan/firm/1", "source": "serp_google"},
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return []

    classifier_calls: list[str] = []

    async def fake_classify_url(url: str, title: str, description: str, log):
        classifier_calls.append(url)
        log.add(
            {
                "call_id": f"call-{len(classifier_calls)}",
                "model": "test",
                "stage": "url_classify",
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_input_tokens": 0,
                "cost_usd": 0.0,
                "duration_ms": 1,
                "success": True,
                "error": None,
            }
        )
        return "garbage" if "article.test" in url else "services"

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)
    monkeypatch.setattr("app.services.leads.pipeline.classify_url", fake_classify_url)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=10,
    )

    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()
    websites = {lead["website"] for lead in result.contacts}

    assert classifier_calls == [
        "https://border.test/company/profile/123",
        "https://article.test/company/profile/123",
    ]
    assert "https://root.test" in websites
    assert "https://contact.test/contacts" in websites
    assert "https://border.test/company/profile/123" in websites
    assert "https://article.test/company/profile/123" not in websites
    assert all(entry["stage"] == "url_classify" for entry in log.llm_calls)


async def test_run_lead_search_prescreens_serp_listicles_before_crawler(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="prescreen@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Рейтинг стоматологий Екатеринбурга",
                "website": "https://rating-root.test",
                "source": "serp_google",
                "website_summary": "Топ-10 стоматологий: список лучших клиник города.",
            },
            {
                "name": "Smile Clinic",
                "website": "https://smile.test",
                "source": "serp_google",
                "website_summary": "Стоматологическая клиника Smile Clinic.",
            },
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    crawled: list[str] = []

    async def fake_crawl_website(website: str, plan: str):
        crawled.append(website)
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="стоматологии",
        city="Екатеринбург",
        limit=10,
    )

    assert crawled == ["https://smile.test"]
    assert result.saved == 1
    assert result.contacts[0]["website"] == "https://smile.test"


async def test_run_lead_search_normalizes_tracking_params_before_url_filter(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="utm-filter@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Smile Clinic",
                "website": "https://smile.test/?utm_source=gmb",
                "phone": "+7 343 222-33-44",
                "source": "serp_maps",
                "website_summary": "Стоматологическая клиника Smile Clinic.",
            },
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    crawled: list[str] = []

    async def fake_crawl_website(website: str, plan: str):
        crawled.append(website)
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="стоматологии",
        city="Екатеринбург",
        limit=1,
    )

    assert result.saved == 1
    assert crawled == ["https://smile.test"]
    assert result.contacts[0]["website"] == "https://smile.test"


async def test_run_lead_search_discards_invalid_contacts_before_scoring(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="validation@test.com", password_hash="hash")
    db_session.add(user)
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Invalid Contact Co",
                "website": "https://invalid-contact.test",
                "email": "not-an-email",
                "phone": "12345",
                "city": city,
                "industry": "Design",
                "source": "serp_google",
                "website_summary": "Design studio with invalid contact fields.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="design studios",
        city="Kazan",
        limit=1,
    )

    lead = (await db_session.execute(select(Lead))).scalar_one()
    contact = result.contacts[0]

    assert lead.email is None
    assert lead.phone is None
    assert contact["email"] is None
    assert contact["phone"] is None
    assert contact["score"] == 55
    assert contact["lead_fit"]["priority"] == "medium"


async def test_run_lead_search_skips_already_contacted_company(monkeypatch, db_session):
    user = User(id=uuid.uuid4(), email="history-skip@test.com", password_hash="hash")
    contact = Contact(
        id=uuid.uuid4(),
        user_id=user.id,
        contact_name="Already Contacted Co",
        email="sales@already.test",
        status="contacted",
    )
    message = CampaignMessage(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        contact_id=contact.id,
        subject="Intro",
        body="Hello",
        status="sent",
        sent_at=datetime.now(UTC),
    )
    db_session.add_all([user, contact, message])
    await db_session.commit()

    async def fake_search_companies(query: str, city: str | None, limit: int):
        return [
            {
                "name": "Already Contacted Co",
                "website": "https://already.test",
                "email": "sales@already.test",
                "phone": None,
                "city": city,
                "source": "serp_google",
                "website_summary": "Company website.",
            }
        ]

    async def fake_generate_queries(query: str, city: str | None, service_offered: str, log):
        return [query]

    async def fake_crawl_website(website: str, plan: str):
        return []

    monkeypatch.setattr("app.services.leads.pipeline.generate_queries", fake_generate_queries)
    monkeypatch.setattr("app.services.leads.pipeline.search_companies", fake_search_companies)
    monkeypatch.setattr("app.services.leads.pipeline.crawl_website", fake_crawl_website)

    result = await run_lead_search(
        db_session,
        user=user,
        query="already contacted companies",
        city="Kazan",
        limit=1,
    )

    log = (await db_session.execute(select(LeadProcessingLog))).scalar_one()

    assert result.saved == 0
    assert log.meta["history_skipped_out"] == 1
    assert log.meta["history_skips"][0]["reason"] == "already_contacted"

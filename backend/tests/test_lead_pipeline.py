import uuid

from sqlalchemy import select

from app.models.lead import Lead, LeadList
from app.models.lead_processing_log import LeadProcessingLog
from app.models.user import User
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

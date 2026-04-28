import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact


def test_claude_client_disabled_without_key(monkeypatch):
    """ClaudeClient raises if anthropic_api_key is empty."""
    monkeypatch.setattr("app.core.config.settings.anthropic_api_key", "")
    from app.services.llm.claude import ClaudeClient
    client = ClaudeClient(model="claude-haiku-4-5-20251001")
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        client._require_key()


@pytest.fixture
async def mock_contact(db_session: AsyncSession):
    c = Contact(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        enrichment=None,
        raw={"website": "https://example.com"},
    )
    return c


@pytest.mark.asyncio
async def test_enrich_contact_disabled(monkeypatch, db_session, mock_contact):
    """Returns immediately when enrichment is disabled."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "disabled")
    db_session.add(mock_contact)
    await db_session.commit()

    from app.services.enrichment import enrich_contact
    result = await enrich_contact(contact_id=str(mock_contact.id), db=db_session)
    assert result == {"enriched": False, "reason": "disabled"}


@pytest.mark.asyncio
async def test_enrich_contact_no_website(monkeypatch, db_session):
    """Skips contact with no website."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "qwen")
    contact = Contact(id=uuid.uuid4(), user_id=uuid.uuid4(), enrichment=None, raw=None)
    db_session.add(contact)
    await db_session.commit()

    from app.services.enrichment import enrich_contact
    result = await enrich_contact(contact_id=str(contact.id), db=db_session)
    assert result == {"enriched": False, "reason": "no_website"}


@pytest.mark.asyncio
async def test_enrich_contact_success(monkeypatch, db_session, mock_contact):
    """Saves summary when Firecrawl + LLM succeed."""
    monkeypatch.setattr("app.core.config.settings.llm_enrich_provider", "qwen")
    db_session.add(mock_contact)
    await db_session.commit()

    fake_scraped = "Компания Example — делает виджеты для B2B."
    fake_summary = (
        '{"description": "Делает виджеты для B2B.", "services": "Виджеты", '
        '"target": "B2B компании", "city": null}'
    )

    with patch("app.services.enrichment._scrape_website", new=AsyncMock(return_value=fake_scraped)), \
         patch("app.services.enrichment._llm_summarize", new=AsyncMock(return_value=fake_summary)):
        from app.services.enrichment import enrich_contact
        result = await enrich_contact(contact_id=str(mock_contact.id), db=db_session)

    assert result["enriched"] is True
    await db_session.refresh(mock_contact)
    assert mock_contact.enrichment["description"] == "Делает виджеты для B2B."

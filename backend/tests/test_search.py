import uuid
from types import SimpleNamespace

from app.services import search as search_module
from app.services.chat import tools as tools_module
from app.services.search import serp as serp_module
from app.services.search.firecrawl import _markdown_to_summary, _scrape_payload


def test_firecrawl_payload_uses_supported_v1_keys():
    payload = _scrape_payload("https://example.com")

    assert payload == {
        "url": "https://example.com",
        "formats": ["markdown"],
        "onlyMainContent": True,
    }


async def test_search_companies_returns_google_maps_results(monkeypatch):
    async def fake_serp(query, city, limit):
        return [{"name": "Studio One", "website": "https://studio.test", "email": None, "phone": "+7 999 000-00-00"}]

    async def fake_google(query, city, limit):
        return []

    async def fake_enrich(url):
        return "Design studio summary"

    async def no_hunter(domain):
        return []

    monkeypatch.setattr(search_module, "search_serp", fake_serp)
    monkeypatch.setattr(search_module, "search_google", fake_google)
    monkeypatch.setattr(search_module, "enrich_website", fake_enrich)
    monkeypatch.setattr(search_module, "find_emails_by_domain", no_hunter)

    results = await search_module.search_companies("design studios", "Kazan", 5)

    assert len(results) == 1
    assert results[0]["name"] == "Studio One"
    assert results[0]["phone"] == "+7 999 000-00-00"
    assert results[0]["website_summary"] == "Design studio summary"


async def test_search_serp_maps_snippet_becomes_website_summary(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "local_results": [
                    {
                        "title": "Studio One",
                        "website": "https://studio.test",
                        "phone": "+7 999 000-00-00",
                        "type": "Design",
                        "address": "Baumana 1",
                        "description": "Design studio for B2B websites.",
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(serp_module.settings, "serpapi_key", "test-key")
    monkeypatch.setattr(serp_module.httpx, "AsyncClient", FakeClient)

    results = await serp_module.search_serp("design studios", "Kazan", 5)

    assert results[0]["website_summary"] == "Design studio for B2B websites."


async def test_search_google_organic_snippet_becomes_website_summary(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "organic_results": [
                    {
                        "title": "Studio One",
                        "link": "https://studio.test/services",
                        "snippet": "Studio One builds conversion-focused B2B websites.",
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(serp_module.settings, "serpapi_key", "test-key")
    monkeypatch.setattr(serp_module.httpx, "AsyncClient", FakeClient)

    results = await serp_module.search_google("design studios", "Kazan", 5)

    assert results[0]["website_summary"] == "Studio One builds conversion-focused B2B websites."


async def test_search_google_filters_article_and_rating_organic_results(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "organic_results": [
                    {
                        "title": "Как выбрать стоматологию: рейтинг клиник",
                        "link": "https://media.test/articles/best-clinics",
                        "snippet": "Топ-10 клиник и отзывы.",
                    },
                    {
                        "title": "Smile Clinic",
                        "link": "https://smile.test",
                        "snippet": "Стоматологическая клиника Smile Clinic.",
                    },
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(serp_module.settings, "serpapi_key", "test-key")
    monkeypatch.setattr(serp_module.httpx, "AsyncClient", FakeClient)

    results = await serp_module.search_google("стоматологии", "Екатеринбург", 5)

    assert [r["website"] for r in results] == ["https://smile.test"]


async def test_search_tool_starts_async_lead_pipeline(monkeypatch):
    calls = []

    async def fake_start_job(db, **kwargs):
        calls.append({"db": db, **kwargs})
        return uuid.UUID("11111111-1111-1111-1111-111111111111")

    monkeypatch.setattr(tools_module, "start_lead_search_job", fake_start_job)
    user = SimpleNamespace(id=uuid.uuid4())
    db = object()

    result = await tools_module._handle_search_companies({
        "__db": db,
        "__user": user,
        "query": "design studios",
        "city": "Kazan",
        "limit": 1,
        "__ai_model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    })

    assert result == {
        "status": "pending",
        "log_id": "11111111-1111-1111-1111-111111111111",
        "query": "design studios",
        "city": "Kazan",
        "limit": 1,
    }
    assert calls[0]["db"] is db
    assert calls[0]["user"] is user
    assert calls[0]["query"] == "design studios"
    assert calls[0]["city"] == "Kazan"
    assert calls[0]["limit"] == 1
    assert calls[0]["list_name"] == "design studios Kazan"
    assert calls[0]["fast_mode"] is True
    assert calls[0]["ai_model"] == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


def test_firecrawl_markdown_summary_skips_navigation_links():
    markdown = """
[Home](https://example.test)
[Contacts](https://example.test/contacts)
# Studio One

Studio One designs B2B websites, product identities, and launch campaigns for technology teams.

- [Portfolio](https://example.test/work)
- [Telegram](https://t.me/example)
"""

    assert _markdown_to_summary(markdown) == (
        "Studio One. Studio One designs B2B websites, product identities, "
        "and launch campaigns for technology teams."
    )

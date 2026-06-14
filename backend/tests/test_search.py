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

    async def no_discovery(*a, **k): return []

    monkeypatch.setattr(search_module, "search_serp", fake_serp)
    monkeypatch.setattr(search_module, "search_google", fake_google)
    monkeypatch.setattr(search_module, "enrich_website", fake_enrich)
    monkeypatch.setattr(search_module, "llm_search_companies", no_discovery)
    monkeypatch.setattr(search_module, "perplexity_search_companies", no_discovery)
    monkeypatch.setattr(search_module, "search_yandex", no_discovery)
    monkeypatch.setattr(search_module, "yandex_search_available", lambda: False)

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
        "limit": 10,
        "__ai_model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    })

    assert result == {
        "status": "pending",
        "log_id": "11111111-1111-1111-1111-111111111111",
        "query": "design studios",
        "city": "Kazan",
        "limit": 10,
    }
    assert calls[0]["db"] is db
    assert calls[0]["user"] is user
    assert calls[0]["query"] == "design studios"
    assert calls[0]["city"] == "Kazan"
    assert calls[0]["limit"] == 10
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


async def test_perplexity_search_parses_and_tags_source(monkeypatch):
    from app.services.llm.base import LLMResult
    from app.services.search import perplexity_search as ps

    async def fake_logged_chat(*args, **kwargs):
        return LLMResult(
            content='{"companies":[{"name":"ООО Тест","website":"https://test.ru","city":"Москва","description":"d"}]}'
        )

    async def fake_head_validate(companies):
        return companies  # skip network check

    monkeypatch.setattr(ps, "logged_chat", fake_logged_chat)
    monkeypatch.setattr(ps, "_head_validate", fake_head_validate)

    out = await ps.perplexity_search_companies("стоматологии", "Москва", count=5)
    assert out == [
        {"name": "ООО Тест", "website": "https://test.ru", "city": "Москва",
         "description": "d", "source": "perplexity"}
    ]


async def test_search_uses_perplexity_when_openrouter_key_present(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "openrouter_api_key", "or-key")
    # LLM discovery (perplexity/Sonar) is opt-in — enable it to exercise this path.
    monkeypatch.setattr(settings, "enable_llm_discovery", True)
    # Disable real Yandex Search so it can't crowd perplexity out of the merged result.
    monkeypatch.setattr(settings, "yandex_api_key", "")
    monkeypatch.setattr(settings, "yandex_folder_id", "")

    async def fake_serp(*a, **k): return []
    async def fake_google(*a, **k): return []
    async def fake_perplexity(niche, city, count):
        return [{"name": "P", "website": "https://p.ru", "source": "perplexity"}]
    async def fake_llm(niche, city, count):
        raise AssertionError("llm_search must not be used when OpenRouter key is set")

    monkeypatch.setattr(search_module, "search_serp", fake_serp)
    monkeypatch.setattr(search_module, "search_google", fake_google)
    monkeypatch.setattr(search_module, "perplexity_search_companies", fake_perplexity)
    monkeypatch.setattr(search_module, "llm_search_companies", fake_llm)

    out = await search_module.search_companies("ниша", "Москва", limit=10, enrich=False)
    assert any(r.get("source") == "perplexity" for r in out)

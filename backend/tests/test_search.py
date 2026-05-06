from app.services import search as search_module
from app.services.chat import tools as tools_module
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


async def test_search_tool_returns_table_ready_company_contract(monkeypatch):
    async def fake_search(query, city, limit):
        return [
            {
                "name": "Studio One",
                "website": "https://studio.test",
                "website_summary": "Design studio for B2B websites and brand systems.",
                "city": city,
                "industry": "Design",
                "address": "Baumana 1",
                "phone": "+7 999 000-00-00",
                "email": None,
                "source": "yandex_maps",
            }
        ]

    monkeypatch.setattr(tools_module, "_search", fake_search)

    result = await tools_module._handle_search_companies({
        "__db": None,
        "__user": None,
        "query": "design studios",
        "city": "Kazan",
        "limit": 1,
    })

    assert result["total"] == 1
    assert result["companies"] == [
        {
            "name": "Studio One",
            "website": "https://studio.test",
            "summary": "Design studio for B2B websites and brand systems.",
            "website_summary": "Design studio for B2B websites and brand systems.",
            "city": "Kazan",
            "industry": "Design",
            "address": "Baumana 1",
            "phone": "+7 999 000-00-00",
            "email": None,
            "source": "yandex_maps",
            "confidence": "inferred",
        }
    ]


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

from app.services import search as search_module
from app.services.search.firecrawl import _scrape_payload


def test_firecrawl_payload_uses_supported_v1_keys():
    payload = _scrape_payload("https://example.com")

    assert payload == {
        "url": "https://example.com",
        "formats": ["markdown"],
        "onlyMainContent": True,
    }


async def test_search_companies_uses_serp_when_twogis_fails(monkeypatch):
    async def broken_twogis(query, city, limit):
        raise RuntimeError("2gis unavailable")

    async def fake_serp(query, city, limit):
        return [{"name": "Fallback Co", "website": "https://fallback.test", "email": None}]

    async def fake_enrich(url):
        return "Fallback summary"

    monkeypatch.setattr(search_module, "search_twogis", broken_twogis)
    monkeypatch.setattr(search_module, "search_serp", fake_serp)
    monkeypatch.setattr(search_module, "enrich_website", fake_enrich)

    results = await search_module.search_companies("design studios", "Kazan", 5)

    assert results == [
        {
            "name": "Fallback Co",
            "website": "https://fallback.test",
            "email": None,
            "website_summary": "Fallback summary",
        }
    ]

from types import SimpleNamespace

from app.services.leads import query_gen as query_gen_module
from app.services.leads.query_gen import generate_queries
from app.services.llm.logged import LoggedLLMCall


async def test_generate_queries_strips_deduplicates_and_caps(monkeypatch):
    async def fake_logged_chat(*args, **kwargs):
        return SimpleNamespace(
            content="""
            {
              "queries": [
                {"query": "  dental clinics Kazan  "},
                {"query": "dental clinics Kazan"},
                {"query": " "},
                {"query": "orthodontics Kazan"},
                {"query": "implants Kazan"},
                {"query": "prosthetics Kazan"},
                {"query": "dentistry services Kazan"},
                {"query": "private dental clinic Kazan"},
                {"query": "family dentistry Kazan"},
                {"query": "children dentistry Kazan"},
                {"query": "emergency dental care Kazan"},
                {"query": "cosmetic dentistry Kazan"}
              ],
              "negative_keywords": ["rating"]
            }
            """
        )

    monkeypatch.setattr(query_gen_module, "get_llm_client", lambda task, **kwargs: object())
    monkeypatch.setattr(query_gen_module, "logged_chat", fake_logged_chat)

    queries = await generate_queries("dental clinics", "Kazan", "website redesign", LoggedLLMCall())

    assert queries == [
        "dental clinics Kazan",
        "orthodontics Kazan",
        "implants Kazan",
        "prosthetics Kazan",
        "dentistry services Kazan",
        "private dental clinic Kazan",
        "family dentistry Kazan",
        "children dentistry Kazan",
        "emergency dental care Kazan",
        "cosmetic dentistry Kazan",
    ]
    assert queries.query_plan.negative_keywords == ["rating"]

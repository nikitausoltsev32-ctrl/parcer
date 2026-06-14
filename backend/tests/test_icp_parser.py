from types import SimpleNamespace

from app.services.leads import icp_parser as icp_parser_module
from app.services.leads.icp import ICPProfile
from app.services.leads.icp_parser import parse_icp
from app.services.llm.logged import LoggedLLMCall


def _stub_llm(monkeypatch, content: str):
    async def fake_logged_chat(*args, **kwargs):
        return SimpleNamespace(content=content)

    monkeypatch.setattr(icp_parser_module, "get_llm_client", lambda task, **kwargs: object())
    monkeypatch.setattr(icp_parser_module, "logged_chat", fake_logged_chat)


async def test_parse_icp_general_query_yields_rich_buyer_segments(monkeypatch):
    _stub_llm(
        monkeypatch,
        """
        {
          "intent": "buyers",
          "seller_summary": "Поставщик упаковки для кофеен",
          "products": ["стаканы", "крышки", "упаковка для еды навынос"],
          "buyer_segments": ["кофейни", "кафе", "HoReCa", "пекарни"],
          "use_cases": ["кофе навынос", "доставка еды"],
          "positive_keywords": ["кофейня", "кафе", "пекарня"],
          "negative_keywords": ["вакансии", "рейтинг"],
          "excluded_industries": ["производители упаковки"]
        }
        """,
    )

    icp = await parse_icp("поставщик упаковки для кофеен", {}, None, log=LoggedLLMCall())

    assert isinstance(icp, ICPProfile)
    assert icp.buyer_segments != ["поставщик упаковки для кофеен"]
    folded = " ".join(icp.buyer_segments).casefold()
    assert "кофейн" in folded or "horeca" in folded or "кафе" in folded


async def test_parse_icp_falls_back_on_malformed_output(monkeypatch):
    _stub_llm(monkeypatch, "not json at all")

    icp = await parse_icp("найди стоматологии в екб", {"offer": "редизайн сайта"}, "Екатеринбург", log=LoggedLLMCall())

    assert isinstance(icp, ICPProfile)
    assert icp.seller_summary


async def test_parse_icp_merges_stored_business_profile_icp(monkeypatch):
    _stub_llm(
        monkeypatch,
        """
        {
          "seller_summary": "LLM summary",
          "buyer_segments": ["кафе"],
          "positive_keywords": ["кофе"]
        }
        """,
    )

    bp = {
        "offer": "упаковка",
        "icp": {
            "buyer_segments": ["рестораны"],
            "excluded_industries": ["агрохимия"],
        },
    }
    icp = await parse_icp("упаковка для кофеен", bp, None, log=LoggedLLMCall())

    assert "рестораны" in icp.buyer_segments
    assert "кафе" in icp.buyer_segments
    assert "агрохимия" in icp.excluded_industries

from app.services.leads.icp import QueryPlan, build_icp_profile, build_query_plan_from_queries
from app.services.leads.icp_filter import has_positive_icp_evidence, reject_by_icp


def test_amp_minerals_icp_rejects_agro_fertilizer_results():
    icp = build_icp_profile(
        {
            "business": "AMP Minerals",
            "offer": "Продажа мраморной крошки и минеральных наполнителей",
            "website": "https://amp-minerals.ru",
        },
        query="покупатели мраморной крошки",
        city=None,
    )
    plan = build_query_plan_from_queries(["производители ЖБИ мраморная крошка"], icp)

    agro = {
        "name": "Агрохимэкспорт",
        "website": "https://agro.test",
        "website_summary": "Минеральные удобрения NPK, сульфат калия и агрохимия для урожая.",
    }
    reject = reject_by_icp(agro, icp=icp, query_plan=plan)

    assert reject is not None
    assert reject.reason == "excluded_keyword"
    assert any("удобр" in term or "npk" in term for term in reject.matched_terms)


def test_amp_minerals_icp_keeps_concrete_and_paving_tile_buyers():
    icp = build_icp_profile(
        {
            "business": "AMP Minerals",
            "offer": "Мраморная крошка для декоративного бетона",
        },
        query="производители бетона и тротуарной плитки",
        city=None,
    )
    plan = build_query_plan_from_queries(["производители тротуарной плитки мраморная крошка"], icp)
    buyer = {
        "name": "Бетон Плитка",
        "website": "https://plitka.test",
        "website_summary": "Производство ЖБИ, декоративного бетона и тротуарной плитки.",
    }

    assert reject_by_icp(buyer, icp=icp, query_plan=plan) is None
    assert has_positive_icp_evidence(buyer, icp=icp, query_plan=plan) is True


def test_icp_filter_ignores_generic_web_noise_negative_terms():
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Мраморная крошка"},
        query="производители ЖБИ",
        city=None,
    )
    plan = QueryPlan(
        queries=["производители ЖБИ"],
        negative_keywords=["новости", "статьи", "вакансии"],
        buyer_segments=icp.buyer_segments,
        excluded_industries=icp.excluded_industries,
        positive_keywords=icp.positive_keywords,
    )
    buyer = {
        "name": "Завод ЖБИ",
        "website": "https://gbi.test",
        "website_summary": "Производство ЖБИ и тротуарной плитки. На сайте есть новости и вакансии.",
    }

    assert reject_by_icp(buyer, icp=icp, query_plan=plan) is None

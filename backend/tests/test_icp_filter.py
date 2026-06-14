from app.services.leads.icp import QueryPlan, build_icp_profile, build_query_plan_from_queries
from app.services.leads.icp_filter import has_positive_icp_evidence, reject_by_icp

_STORED_ICP = {
    "seller_summary": "Поставщик мраморной крошки и минеральных наполнителей",
    "products": ["мраморная крошка", "минеральные наполнители"],
    "buyer_segments": [
        "производители ЖБИ",
        "производители тротуарной плитки",
        "производители декоративного бетона",
    ],
    "positive_keywords": ["жби", "бетон", "тротуарная плитка", "декоративный бетон"],
    "negative_keywords": ["удобр", "агрохим", "npk", "сульфат калия"],
    "excluded_industries": ["минеральные удобрения", "агрохимия"],
}


def test_stored_icp_rejects_agro_fertilizer_results():
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Продажа мраморной крошки", "icp": _STORED_ICP},
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


def test_stored_icp_keeps_concrete_and_paving_tile_buyers():
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Мраморная крошка для бетона", "icp": _STORED_ICP},
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


def test_short_negative_stem_does_not_false_match_inside_word():
    # LLM may emit a short negative stem like "сад" (садоводство). It must NOT reject a
    # facade-materials maker ("фасад" contains "сад") — that's a valid marble buyer.
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Мраморная крошка", "icp": _STORED_ICP},
        query="производители фасадных материалов",
        city=None,
    )
    plan = QueryPlan(
        queries=["фасадные штукатурки мраморная крошка"],
        negative_keywords=["сад", "корм"],
        buyer_segments=icp.buyer_segments,
        excluded_industries=icp.excluded_industries,
        positive_keywords=icp.positive_keywords,
    )
    buyer = {
        "name": "ФасадСтрой",
        "website": "https://fasad.test",
        "website_summary": "Производство фасадных штукатурок и декоративного бетона.",
    }
    assert reject_by_icp(buyer, icp=icp, query_plan=plan) is None


def test_negative_stem_still_matches_at_word_start_with_suffix():
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Мраморная крошка", "icp": _STORED_ICP},
        query="мраморная крошка",
        city=None,
    )
    plan = build_query_plan_from_queries(["мраморная крошка"], icp)
    agro = {
        "name": "АгроМикс",
        "website": "https://agromix.test",
        "website_summary": "Удобрения и почвосмеси для урожая.",  # "Удобрения" starts with stem "удобр"
    }
    reject = reject_by_icp(agro, icp=icp, query_plan=plan)
    assert reject is not None
    assert "удобр" in reject.matched_terms


def test_icp_filter_ignores_generic_web_noise_negative_terms():
    icp = build_icp_profile(
        {"business": "AMP Minerals", "offer": "Мраморная крошка", "icp": _STORED_ICP},
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

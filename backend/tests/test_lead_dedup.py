from app.services.leads.dedup import deduplicate_candidates


def test_deduplicate_candidates_prefers_higher_score_for_same_domain():
    result = deduplicate_candidates(
        [
            {"name": "Studio One", "website": "https://studio.test", "score": 40},
            {"name": "Studio One Plus", "website": "https://www.studio.test/about", "score": 90},
        ]
    )

    assert result == [{"name": "Studio One Plus", "website": "https://www.studio.test/about", "score": 90}]


def test_deduplicate_candidates_matches_normalized_legal_name():
    result = deduplicate_candidates(
        [
            {"name": "ООО Ромашка", "website": None, "score": 30},
            {"name": "ромашка", "website": None, "score": 50},
        ]
    )

    assert result == [{"name": "ромашка", "website": None, "score": 50}]


def test_deduplicate_candidates_matches_fuzzy_name_without_domain():
    result = deduplicate_candidates(
        [
            {"name": "Dental Studio Smile", "website": None, "score": 60},
            {"name": "Dental Studio Smiles", "website": None, "score": 20},
        ]
    )

    assert result == [{"name": "Dental Studio Smile", "website": None, "score": 60}]


def test_deduplicate_candidates_keeps_different_companies():
    result = deduplicate_candidates(
        [
            {"name": "Studio Alpha", "website": None, "score": 30},
            {"name": "Clinic Beta", "website": None, "score": 40},
        ]
    )

    assert result == [
        {"name": "Studio Alpha", "website": None, "score": 30},
        {"name": "Clinic Beta", "website": None, "score": 40},
    ]


def test_deduplicate_candidates_returns_empty_list():
    assert deduplicate_candidates([]) == []

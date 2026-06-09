from app.services.leads.scoring import score_candidate


def test_score_candidate_prioritizes_site_and_contacts():
    result = score_candidate(
        {
            "name": "Studio One",
            "website": "https://studio.test",
            "email": "hello@studio.test",
            "phone": "+7 999 000-00-00",
            "website_summary": "B2B website studio",
        }
    )

    # Mechanical scoring (no AI signal) is capped below "medium" by design
    assert result.score == 49
    assert result.priority == "low"
    assert result.confidence == "verified"


def test_score_candidate_uses_ai_score_with_contact_bonuses():
    result = score_candidate(
        {
            "name": "Studio One",
            "website": "https://studio.test",
            "email": "hello@studio.test",
            "phone": "+7 999 000-00-00",
            "ai_score": 70,
            "ai_reason": "ICP fit",
        }
    )

    assert result.score == 83
    assert result.priority == "high"


def test_score_candidate_does_not_inflate_missing_contacts():
    result = score_candidate({"name": "Studio One", "website": None, "email": None, "phone": None})

    assert result.score < 50
    assert result.priority == "low"
    assert result.confidence == "missing"

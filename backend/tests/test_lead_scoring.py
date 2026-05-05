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

    assert result.score >= 80
    assert result.priority == "high"
    assert result.confidence == "verified"


def test_score_candidate_does_not_inflate_missing_contacts():
    result = score_candidate({"name": "Studio One", "website": None, "email": None, "phone": None})

    assert result.score < 50
    assert result.priority == "low"
    assert result.confidence == "missing"

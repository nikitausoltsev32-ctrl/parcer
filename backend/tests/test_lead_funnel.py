from app.services.leads.funnel import has_any_channel, is_generic_email


def test_is_generic_email_detects_role_mailboxes():
    assert is_generic_email("info@studio.ru") is True
    assert is_generic_email("SALES@studio.ru") is True
    assert is_generic_email("zakaz@studio.ru") is True


def test_is_generic_email_treats_personal_local_part_as_not_generic():
    assert is_generic_email("ivan.petrov@studio.ru") is False
    assert is_generic_email("a.smirnova@studio.ru") is False


def test_is_generic_email_handles_empty_and_malformed():
    assert is_generic_email(None) is False
    assert is_generic_email("") is False
    assert is_generic_email("not-an-email") is False


def test_has_any_channel_true_when_any_contact_present():
    assert has_any_channel({"email": "info@x.ru"}) is True
    assert has_any_channel({"phone": "+7 999 000-00-00"}) is True
    assert has_any_channel({"telegram": "https://t.me/x"}) is True
    assert has_any_channel({"whatsapp": "https://wa.me/79990000000"}) is True
    assert has_any_channel({"has_contact_form": True}) is True


def test_has_any_channel_false_when_no_contact():
    assert has_any_channel({"email": None, "phone": None, "has_contact_form": False}) is False
    assert has_any_channel({}) is False


from app.services.leads.funnel import FunnelStats, compute_funnel


def _leads_fixture():
    return [
        {"source": "serp_maps", "email": "ivan@a.ru", "phone": "+7 999 000-00-00", "score": 82},
        {"source": "serp_google", "email": "info@b.ru", "phone": None, "score": 71},
        {"source": "perplexity", "email": None, "phone": None, "telegram": "https://t.me/c", "score": 40},
        {"source": "serp_google", "email": None, "phone": None, "has_contact_form": False, "score": 55},
    ]


def test_compute_funnel_counts_channels_emails_and_high_scores():
    stats = compute_funnel(
        "стоматологии",
        "Екатеринбург",
        urls_found=200,
        urls_after_filter=80,
        urls_crawled=20,
        pages_crawled=60,
        serp_prescreened_out=12,
        icp_rejected_out=30,
        history_skipped_out=4,
        leads=_leads_fixture(),
    )
    assert isinstance(stats, FunnelStats)
    assert stats.saved == 4
    assert stats.with_any_channel == 3
    assert stats.with_email == 2
    assert stats.with_personal_email == 1
    assert stats.score_70_plus == 2
    assert stats.source_counts == {"serp_maps": 1, "serp_google": 2, "perplexity": 1}


def test_compute_funnel_handles_empty_leads():
    stats = compute_funnel(
        "ниша",
        None,
        urls_found=0,
        urls_after_filter=0,
        urls_crawled=0,
        pages_crawled=0,
        serp_prescreened_out=0,
        icp_rejected_out=0,
        history_skipped_out=0,
        leads=[],
    )
    assert stats.saved == 0
    assert stats.with_any_channel == 0
    assert stats.source_counts == {}


def test_compute_funnel_buckets_unknown_source():
    stats = compute_funnel(
        "ниша", None,
        urls_found=1, urls_after_filter=1, urls_crawled=1, pages_crawled=1,
        serp_prescreened_out=0, icp_rejected_out=0, history_skipped_out=0,
        leads=[{"score": 10}],
    )
    assert stats.source_counts == {"unknown": 1}


from app.services.leads.funnel import format_funnel_table, funnel_to_csv_rows


def _stats_fixture():
    return compute_funnel(
        "стоматологии",
        "Екатеринбург",
        urls_found=200,
        urls_after_filter=80,
        urls_crawled=20,
        pages_crawled=60,
        serp_prescreened_out=12,
        icp_rejected_out=30,
        history_skipped_out=4,
        leads=[
            {"source": "serp_maps", "email": "ivan@a.ru", "score": 82},
            {"source": "perplexity", "email": "info@b.ru", "score": 40},
        ],
    )


def test_funnel_to_csv_rows_splits_serp_and_llm_sources():
    rows = funnel_to_csv_rows([_stats_fixture()])
    assert len(rows) == 1
    row = rows[0]
    assert row["niche"] == "стоматологии"
    assert row["city"] == "Екатеринбург"
    assert row["urls_found"] == 200
    assert row["urls_after_filter"] == 80
    assert row["saved"] == 2
    assert row["with_any_channel"] == 2
    assert row["with_personal_email"] == 1
    assert row["score_70_plus"] == 1
    assert row["serp_count"] == 1
    assert row["llm_count"] == 1


def test_format_funnel_table_contains_niche_and_numbers():
    table = format_funnel_table([_stats_fixture()])
    assert "стоматологии" in table
    assert "200" in table
    assert "saved" in table.lower()

from app.services.leads.url_filter import BLOCKED_DOMAINS, filter_urls, is_blocked_domain


def test_blocks_medical_aggregators_that_used_to_leak():
    for host in ("napopravku.ru", "docdoc.ru", "sberhealth.ru", "32top.ru", "prodoctorov.ru"):
        assert is_blocked_domain(f"https://{host}/clinic/123") is True


def test_blocks_business_catalogs():
    for host in ("rusprofile.ru", "list-org.com", "orgpage.ru", "spr.ru", "cataloxy.ru"):
        assert is_blocked_domain(f"https://{host}/company") is True


def test_blocks_subdomains_of_aggregators():
    assert is_blocked_domain("https://ekb.docdoc.ru/lpu/45") is True
    assert is_blocked_domain("https://msk.zoon.ru/medical/") is True


def test_keeps_real_company_site():
    assert is_blocked_domain("https://example-dental.ru/uslugi") is False


def test_serp_reuses_the_same_canonical_set():
    from app.services.search.serp import _AGGREGATOR_DOMAINS

    assert _AGGREGATOR_DOMAINS is BLOCKED_DOMAINS


def test_filter_urls_drops_aggregators_and_dedupes():
    urls = [
        "https://example-dental.ru/",
        "https://docdoc.ru/clinic/1",
        "https://example-dental.ru/contacts",  # same domain, deduped
    ]
    assert filter_urls(urls) == ["https://example-dental.ru/"]

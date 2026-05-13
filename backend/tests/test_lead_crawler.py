from app.services.leads.crawler import _candidate_urls, _extract_contact_links


def test_candidate_urls_prioritizes_landing_and_contacts_for_trial_limit():
    assert _candidate_urls("https://studio.test", 2) == [
        "https://studio.test/",
        "https://studio.test/contacts",
    ]


def test_extract_contact_links_discovers_non_standard_contacts_path():
    html = """
    <html>
      <body>
        <a href="/services">Services</a>
        <a href="/company/contacts">Контакты</a>
        <a href="/blog/contacts-in-sales">Blog</a>
      </body>
    </html>
    """

    assert _extract_contact_links(html, "https://studio.test/") == [
        "https://studio.test/company/contacts",
    ]

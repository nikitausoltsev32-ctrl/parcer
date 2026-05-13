from app.services.leads.extraction import (
    extract_all_emails,
    extract_inn,
    extract_public_contacts,
    normalize_domain,
    normalize_phone_e164,
    normalize_website,
)
from app.services.leads.html_extraction import extract_from_html


def test_normalize_website_adds_scheme_and_strips_tracking_path_noise():
    assert normalize_website("www.example.ru/contacts?utm_source=ad") == "https://www.example.ru/contacts"


def test_normalize_domain_removes_www_and_path():
    assert normalize_domain("https://www.example.ru/contacts") == "example.ru"


def test_extract_public_contacts_finds_real_contacts_and_social_links():
    text = """
    Связь: hello@example.ru, +7 (343) 222-33-44.
    Telegram: https://t.me/example_sales
    WhatsApp: https://wa.me/73432223344
    VK: https://vk.com/example
    """

    result = extract_public_contacts(text)

    assert result.email == "hello@example.ru"
    assert result.phone == "+7 (343) 222-33-44"
    assert result.telegram == "https://t.me/example_sales"
    assert result.whatsapp == "https://wa.me/73432223344"
    assert result.vk == "https://vk.com/example"


def test_extract_public_contacts_returns_none_without_fabricating_data():
    result = extract_public_contacts("Компания делает сайты. Контакты скрыты.")

    assert result.email is None
    assert result.phone is None
    assert result.telegram is None
    assert result.whatsapp is None
    assert result.vk is None


def test_extract_from_html_returns_og_schema_and_business_summary():
    html = """
    <html>
      <head>
        <title>Studio One</title>
        <meta property="og:description" content="OG summary for Studio One.">
        <script type="application/ld+json">
          {"@type": "LocalBusiness", "description": "Schema summary for Studio One."}
        </script>
      </head>
      <body>
        <nav>Home Contacts Blog</nav>
        <h1>Studio One</h1>
        <h2>B2B websites and brand systems</h2>
        <p>Studio One builds conversion-focused websites and brand systems for B2B teams.</p>
      </body>
    </html>
    """

    result = extract_from_html(html, "https://studio.test")

    assert result["og_description"] == "OG summary for Studio One."
    assert result["schema_org_description"] == "Schema summary for Studio One."
    expected_summary = "Studio One builds conversion-focused websites and brand systems for B2B teams."
    assert result["first_text_block"] == expected_summary
    assert result["business_summary"] == expected_summary


def test_extract_from_html_finds_obfuscated_footer_email():
    html = """
    <html>
      <body>
        <main><h1>Studio One</h1><p>We build B2B websites.</p></main>
        <footer>
          <div>Contacts</div>
          <div>Email: sales [at] studio [dot] test</div>
          <div>Phone: +7 (343) 222-33-44</div>
        </footer>
      </body>
    </html>
    """

    result = extract_from_html(html, "https://studio.test")

    assert result["email"] == "sales@studio.test"
    assert result["phone"] == "+7 (343) 222-33-44"
    assert "sales [at] studio [dot] test" in result["footer_text"]


def test_extract_from_html_finds_cyrillic_obfuscated_email():
    html = """
    <html>
      <body>
        <main><h1>Studio One</h1><p>We build B2B websites.</p></main>
        <footer>Почта: sales [собака] studio [точка] test</footer>
      </body>
    </html>
    """

    result = extract_from_html(html, "https://studio.test")

    assert result["email"] == "sales@studio.test"


def test_extract_from_html_prioritizes_about_section_for_business_summary():
    html = """
    <html>
      <body>
        <main>
          <h1>Prom Tech</h1>
          <p>Short hero text for the first screen that should not be the main business summary.</p>
          <section id="about">
            <h2>О компании</h2>
            <p>Prom Tech designs and maintains industrial automation systems for manufacturing plants.</p>
            <p>The company works with production lines, dispatching, and service support.</p>
          </section>
        </main>
      </body>
    </html>
    """

    result = extract_from_html(html, "https://prom-tech.test")

    assert result["about_text"].startswith("О компании Prom Tech designs and maintains industrial automation")
    assert result["business_summary"] == result["about_text"]

def test_normalize_phone_e164_converts_russian_8_prefix():
    assert normalize_phone_e164("8 (999) 123-45-67") == "+79991234567"


def test_normalize_phone_e164_keeps_plus_7_number():
    assert normalize_phone_e164("+7 999 123-45-67") == "+79991234567"


def test_normalize_phone_e164_rejects_short_number():
    assert normalize_phone_e164("123-45-67") is None


def test_normalize_phone_e164_returns_none_for_empty_value():
    assert normalize_phone_e164(None) is None


def test_extract_inn_returns_number_with_context():
    assert extract_inn("Реквизиты: ИНН 7707083893, КПП 770701001") == "7707083893"


def test_extract_inn_ignores_number_without_context():
    assert extract_inn("Код заявки 7707083893 создан автоматически") is None


def test_extract_inn_returns_none_for_empty_value():
    assert extract_inn(None) is None


def test_extract_all_emails_returns_unique_lowercase_emails():
    assert extract_all_emails("Sales@Example.ru, sales@example.ru; info@example.ru") == [
        "sales@example.ru",
        "info@example.ru",
    ]

from app.services.leads.extraction import (
    extract_all_emails,
    extract_inn,
    extract_public_contacts,
    normalize_domain,
    normalize_phone_e164,
    normalize_website,
)


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

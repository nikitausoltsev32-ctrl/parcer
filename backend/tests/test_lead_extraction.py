from app.services.leads.extraction import (
    extract_public_contacts,
    normalize_domain,
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

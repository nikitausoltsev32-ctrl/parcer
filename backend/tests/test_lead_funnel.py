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

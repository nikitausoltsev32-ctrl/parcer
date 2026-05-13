from app.core import email as email_module


def test_send_email_skips_smtp_when_credentials_are_missing(monkeypatch):
    calls = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(email_module.settings, "transactional_smtp_host", "smtp.example.test")
    monkeypatch.setattr(email_module.settings, "transactional_smtp_user", "")
    monkeypatch.setattr(email_module.settings, "transactional_smtp_pass", "")
    monkeypatch.setattr(email_module.smtplib, "SMTP_SSL", FakeSMTP)

    email_module.send_email("user@example.test", "Subject", "<p>Body</p>")

    assert calls == []

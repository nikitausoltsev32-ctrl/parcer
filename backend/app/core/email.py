import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(to: str, subject: str, html_body: str) -> None:
    if not settings.transactional_smtp_host:
        print(f"[EMAIL] To: {to} | Subject: {subject}\n{html_body}\n")
        return
    if not settings.transactional_smtp_user or not settings.transactional_smtp_pass:
        print(f"[EMAIL SKIPPED] SMTP credentials are not configured. To: {to} | Subject: {subject}\n")
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.transactional_from_email
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(
            settings.transactional_smtp_host,
            settings.transactional_smtp_port,
            context=ctx,
            timeout=10,
        ) as server:
            server.login(settings.transactional_smtp_user, settings.transactional_smtp_pass)
            server.sendmail(settings.transactional_from_email, to, msg.as_string())
    except Exception as e:
        print(f"[EMAIL ERROR] To: {to} | {e}\nSubject: {subject}\n{html_body}\n")


def send_verify_email(to: str, token: str) -> None:
    url = f"{settings.frontend_url}/verify-email?token={token}"
    send_email(to=to, subject="Подтвердите email — parcer", html_body=f'<p>Подтвердите email: <a href="{url}">Подтвердить</a> (действует 24 часа)</p>')


def send_reset_password_email(to: str, token: str) -> None:
    url = f"{settings.frontend_url}/reset-password?token={token}"
    send_email(to=to, subject="Сброс пароля — parcer", html_body=f'<p>Сбросить пароль: <a href="{url}">Сбросить</a> (действует 1 час)</p>')

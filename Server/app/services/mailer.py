import logging
import smtplib
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)


class Mailer(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleMailer:
    def send(self, *, to: str, subject: str, body: str) -> None:
        print(
            f"\n{'=' * 62}\nMAIL (console backend)\nTo:      {to}\n"
            f"Subject: {subject}\n\n{body}\n{'=' * 62}\n",
            flush=True,
        )


class GmailMailer:
    def __init__(self, *, host: str, port: int, user: str, password: str, sender: str):
        self._host, self._port = host, port
        self._user, self._password = user, password
        self._sender = sender

    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(self._user, self._password)
            smtp.send_message(message)


@lru_cache
def get_mailer() -> Mailer:
    settings = get_settings()
    if settings.mail_backend == "console":
        # The console backend prints login codes to stdout. That is the point in
        # dev and a credential leak anywhere else.
        if settings.env == "production":
            raise RuntimeError("MAIL_BACKEND=console is refused when ENV=production")
        return ConsoleMailer()
    if not (settings.gmail_user and settings.gmail_app_password):
        raise RuntimeError("MAIL_BACKEND=gmail needs GMAIL_USER and GMAIL_APP_PASSWORD")
    return GmailMailer(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.gmail_user,
        password=settings.gmail_app_password,
        sender=settings.mail_from or settings.gmail_user,
    )


def send_login_code(to: str, code: str) -> None:
    minutes = get_settings().otp_ttl_minutes
    get_mailer().send(
        to=to,
        subject="Your Book Shelf login code",
        body=(
            f"Your login code is {code}\n\n"
            f"It expires in {minutes} minutes and can be used once.\n"
            "If you did not try to sign in, someone has your password: change it."
        ),
    )


def send_reset_token(to: str, token: str) -> None:
    minutes = get_settings().reset_token_ttl_minutes
    get_mailer().send(
        to=to,
        subject="Reset your Book Shelf password",
        body=(
            f"Your password reset token is:\n\n{token}\n\n"
            f"It expires in {minutes} minutes and can be used once.\n"
            "If you did not request this, you can ignore this email."
        ),
    )

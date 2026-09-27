"""Optional external delivery, isolated from complaint transactions."""

import os
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import select

from .db import now
from .models import Delivery, Notification, User


class EmailProvider(Protocol):
    def send(self, recipient: str, message: str) -> None: ...


class SMTPProvider:
    def send(self, recipient, message):
        mail = EmailMessage()
        mail["From"] = os.environ["SMTP_FROM"]
        mail["To"] = recipient
        mail["Subject"] = "CleanCity complaint update"
        mail.set_content(message + "\nSign in to your municipal portal for details.")
        with smtplib.SMTP(
            os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=10
        ) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if os.getenv("SMTP_USERNAME"):
                smtp.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
            smtp.send_message(mail)


def email_provider():
    if os.getenv("EMAIL_PROVIDER") == "smtp" and os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"):
        return SMTPProvider()
    return None


def dispatch(db):
    provider = email_provider()
    for delivery in db.scalars(
        select(Delivery)
        .where(Delivery.status.in_(["PENDING", "RETRY"]), Delivery.next_attempt <= now())
        .limit(25)
    ):
        if provider is None:
            delivery.status = "NOT_CONFIGURED"
            continue
        notice = db.get(Notification, delivery.notification_id)
        user = db.get(User, notice.user_id)
        if not user.active:
            delivery.status = "SKIPPED_INACTIVE"
            continue
        delivery.attempts += 1
        try:
            provider.send(user.email, notice.message)
            delivery.status = "SENT"
            delivery.last_error = ""
        except (OSError, smtplib.SMTPException, KeyError) as error:
            delivery.last_error = type(error).__name__
            delivery.status = "FAILED" if delivery.attempts >= 3 else "RETRY"
            delivery.next_attempt = now() + timedelta(minutes=5 * delivery.attempts)
    db.commit()

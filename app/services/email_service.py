from __future__ import annotations

import logging
from typing import Iterable, Mapping, Any

from flask import current_app, render_template
from flask_mail import Message
from jinja2 import TemplateNotFound

from app.extensions import mail

logger = logging.getLogger(__name__)


DEFAULT_SENDER_NAME = "Machine Pulse"  # placeholder brand name


def _default_sender() -> str | None:
    sender = current_app.config.get("MAIL_DEFAULT_SENDER") if current_app else None
    if sender and "<" in sender:
        return sender
    if sender:
        return f"{DEFAULT_SENDER_NAME} <{sender}>"
    return None


def send_email(
    *,
    subject: str,
    recipients: Iterable[str],
    template: str,
    context: Mapping[str, Any] | None = None,
    sender: str | None = None,
    reply_to: str | None = None,
) -> None:
    recips = [r for r in recipients if r]
    if not recips:
        return
    if not mail:
        logger.info("Mail extension not configured; skipping send for %s", subject)
        return

    ctx = dict(context or {})
    try:
        html_body = render_template(f"emails/{template}.html", **ctx)
    except TemplateNotFound:
        logger.error("Missing HTML email template: emails/%s.html", template)
        return

    try:
        text_body = render_template(f"emails/{template}.txt", **ctx)
    except TemplateNotFound:
        text_body = "This email requires an email client that supports HTML."

    msg = Message(
        subject=subject,
        recipients=recips,
        sender=sender or _default_sender(),
        reply_to=reply_to,
        body=text_body,
        html=html_body,
    )

    try:
        mail.send(msg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email send failed: %s", exc)

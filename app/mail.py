import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def inbox_email():
    return (
        os.environ.get("INBOX_EMAIL", "").strip()
        or "africloudinstitute@gmail.com"
    )


def send_inbox_email(subject, body, reply_to=None):
    """Send a notification to the AfriCloud applications inbox."""
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or user
    recipient = inbox_email()

    if not user or not password or not sender:
        logger.error("SMTP is not configured; inbox email was not sent: %s", subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("Failed to send inbox email: %s", subject)
        return False


def format_fields(fields):
    lines = []
    for label, value in fields:
        text = value if value else "—"
        if isinstance(text, list):
            text = ", ".join(text) if text else "—"
        lines.append(f"{label}: {text}")
    return "\n".join(lines)

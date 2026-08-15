import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def inbox_email():
    return (
        os.environ.get("INBOX_EMAIL", "").strip()
        or "africloudinstitute@gmail.com"
    )


def _on_render():
    return os.environ.get("RENDER", "").lower() in {"true", "1"}


def send_inbox_email(subject, body, reply_to=None):
    """Send a notification to the AfriCloud applications inbox."""
    if _on_render():
        return _send_formsubmit(subject, body, reply_to)
    if _send_smtp(subject, body, reply_to):
        return True
    return _send_formsubmit(subject, body, reply_to)


def _send_smtp(subject, body, reply_to=None):
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
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
        logger.info("SMTP inbox email sent: %s", subject)
        return True
    except Exception:
        logger.exception("Failed to send inbox email over SMTP: %s", subject)
        return False


def _send_formsubmit(subject, body, reply_to=None):
    """Deliver over HTTPS so Render's free plan (SMTP ports blocked) can still send."""
    recipient = inbox_email()
    payload = {
        "_subject": subject,
        "_captcha": "false",
        "_template": "box",
        "subject": subject,
        "message": body,
    }
    if reply_to:
        payload["_replyto"] = reply_to
        payload["reply_to"] = reply_to

    request = urllib.request.Request(
        f"https://formsubmit.co/ajax/{recipient}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AfriCloudInstitute/1.0",
            "Origin": os.environ.get("SERVICE_URL", "https://africloud-institute.onrender.com"),
            "Referer": os.environ.get(
                "SERVICE_URL", "https://africloud-institute.onrender.com"
            )
            + "/apply",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        success = str(result.get("success", "")).lower() == "true"
        if success:
            logger.info("HTTPS inbox email sent: %s", subject)
            return True
        logger.error("HTTPS inbox email was not accepted: %s %s", subject, result)
        return False
    except urllib.error.HTTPError as error:
        logger.error("HTTPS inbox email HTTP error: %s %s", error.code, error.read()[:500])
        return False
    except Exception:
        logger.exception("Failed to send inbox email over HTTPS: %s", subject)
        return False


def format_fields(fields):
    lines = []
    for label, value in fields:
        text = value if value else "—"
        if isinstance(text, list):
            text = ", ".join(text) if text else "—"
        lines.append(f"{label}: {text}")
    return "\n".join(lines)

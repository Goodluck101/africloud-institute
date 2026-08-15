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


def applicant_confirmation_text(site, name, course):
    first_name = (name or "there").strip().split()[0] or "there"
    title = course.get("title", "your programme")
    duration = course.get("duration", "")
    start = course.get("start_date", "")
    programme = f"{title} ({duration})" if duration else title
    contact_email = site.get("applications_email") or site.get("email") or inbox_email()
    phone = site.get("phone_display") or site.get("phone") or ""
    institute = site.get("name", "AfriCloud Institute")

    lines = [
        f"Hi {first_name},",
        "",
        f"Thank you for applying to {programme} at {institute}.",
        "",
        "We have received your application. Our team will contact you by email or phone with cohort dates, fees, and next steps.",
    ]
    if start:
        lines.extend(["", f"The next cohort is currently listed as starting {start}."])
    lines.extend(
        [
            "",
            "If you are admitted, we will invite you to the cohort WhatsApp group.",
            "",
            institute,
            contact_email,
            phone,
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def send_inbox_email(subject, body, reply_to=None, autoresponse=None, cc=None):
    """Send a notification to the AfriCloud applications inbox."""
    if _on_render():
        return _send_formsubmit(subject, body, reply_to, autoresponse=autoresponse, cc=cc)
    if _send_smtp_to(inbox_email(), subject, body, reply_to=reply_to):
        return True
    return _send_formsubmit(subject, body, reply_to, autoresponse=autoresponse, cc=cc)


def send_applicant_email(to_email, subject, body):
    """Email the applicant a brief confirmation."""
    to_email = (to_email or "").strip()
    if not to_email:
        return False
    if not _on_render() and _send_smtp_to(to_email, subject, body, reply_to=inbox_email()):
        return True
    return _send_formsubmit(subject, body, reply_to=to_email, cc=to_email)


def _send_smtp_to(recipient, subject, body, reply_to=None):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or user

    if not user or not password or not sender:
        logger.error("SMTP is not configured; email was not sent: %s", subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"AfriCloud Institute <{sender}>"
    message["To"] = recipient
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
        logger.info("SMTP email sent to %s: %s", recipient, subject)
        return True
    except Exception:
        logger.exception("Failed to send SMTP email to %s: %s", recipient, subject)
        return False


def _send_formsubmit(subject, body, reply_to=None, autoresponse=None, cc=None):
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
        payload["email"] = reply_to
    if cc:
        payload["_cc"] = cc
    if autoresponse:
        payload["_autoresponse"] = autoresponse

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

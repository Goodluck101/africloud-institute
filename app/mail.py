import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from flask import render_template

logger = logging.getLogger(__name__)


def inbox_email():
    return (
        os.environ.get("INBOX_EMAIL", "").strip()
        or "africloudinstitute@gmail.com"
    )


def sender_email():
    return os.environ.get("SMTP_FROM", "").strip() or inbox_email()


def _on_render():
    return os.environ.get("RENDER", "").lower() in {"true", "1"}


def public_base_url():
    return (
        os.environ.get("PUBLIC_BASE_URL", "").strip()
        or os.environ.get("SERVICE_URL", "").strip()
        or "https://africloud-institute.onrender.com"
    )


def _logo_url(site):
    logo = (site or {}).get("logo") or "/static/images/logo.jpg"
    if logo.startswith("http"):
        return logo
    return public_base_url().rstrip("/") + logo


def _first_name(name):
    return (name or "there").strip().split()[0] or "there"


def applicant_confirmation_text(site, name, course):
    first_name = _first_name(name)
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


def _applicant_confirmation_html(site, name, course):
    title = course.get("title", "your programme")
    duration = course.get("duration", "")
    programme = f"{title} ({duration})" if duration else title
    return render_template(
        "email/applicant_confirmation.html",
        subject=f"We received your application for {title}",
        site=site,
        logo_url=_logo_url(site),
        first_name=_first_name(name),
        programme=programme,
        course=course,
    )


def _staff_notice_html(site, kicker, heading, intro, rows, subject):
    return render_template(
        "email/staff_notice.html",
        subject=subject,
        site=site,
        logo_url=_logo_url(site),
        kicker=kicker,
        heading=heading,
        intro=intro,
        rows=[{"label": label, "value": value or "—"} for label, value in rows],
    )


def send_email(to_email, subject, text, html=None, reply_to=None):
    """Send from AfriCloud Institute Gmail. SMTP locally; HTTPS Gmail relay on Render."""
    to_email = (to_email or "").strip()
    if not to_email:
        return False

    if not _on_render() and _send_smtp(to_email, subject, text, html, reply_to):
        return True
    if _send_gmail_webhook(to_email, subject, text, html, reply_to):
        return True
    if _on_render():
        logger.error("Gmail webhook is not configured; email was not sent: %s", subject)
        return False
    return _send_smtp(to_email, subject, text, html, reply_to)


def send_inbox_email(subject, body, reply_to=None, html=None, **_unused):
    return send_email(inbox_email(), subject, body, html=html, reply_to=reply_to)


def send_applicant_email(to_email, subject, body, html=None):
    return send_email(to_email, subject, body, html=html, reply_to=inbox_email())


def notify_application(site, record, course):
    rows = [
        ("Name", record.get("full_name")),
        ("Email", record.get("email")),
        ("Phone", record.get("phone")),
        ("City", record.get("city")),
        ("Programme", record.get("programme_title")),
        ("Experience", record.get("experience")),
        ("Motivation", record.get("motivation")),
        ("Submitted at", record.get("submitted_at")),
    ]
    staff_subject = f"Programme application: {course.get('title', '')}"
    staff_text = "New application from the AfriCloud Institute website.\n\n" + format_fields(rows)
    staff_html = _staff_notice_html(
        site,
        "New application",
        course.get("title", "Programme application"),
        "A learner submitted an application on the website.",
        rows,
        staff_subject,
    )
    send_inbox_email(staff_subject, staff_text, reply_to=record.get("email"), html=staff_html)

    confirm_subject = f"We received your application for {course.get('title', 'your programme')}"
    confirm_text = applicant_confirmation_text(site, record.get("full_name"), course)
    confirm_html = _applicant_confirmation_html(site, record.get("full_name"), course)
    return send_applicant_email(record.get("email"), confirm_subject, confirm_text, html=confirm_html)


def notify_contact(site, record):
    rows = [
        ("Name", record.get("full_name")),
        ("Email", record.get("email")),
        ("Phone", record.get("phone")),
        ("Message", record.get("message")),
        ("Submitted at", record.get("submitted_at")),
    ]
    subject = f"Website enquiry from {record.get('full_name', '')}"
    text = "New contact message from the AfriCloud Institute website.\n\n" + format_fields(rows)
    html = _staff_notice_html(
        site,
        "New enquiry",
        "Website contact message",
        "Someone sent a message from the Contact page.",
        rows,
        subject,
    )
    return send_inbox_email(subject, text, reply_to=record.get("email"), html=html)


def notify_corporate(site, record):
    programmes = record.get("programmes") or []
    if isinstance(programmes, list):
        programmes = ", ".join(programmes)
    rows = [
        ("Company", record.get("company_name")),
        ("Contact", record.get("contact_name")),
        ("Job title", record.get("job_title")),
        ("Email", record.get("email")),
        ("Phone", record.get("phone")),
        ("Team size", record.get("team_size")),
        ("Preferred start", record.get("preferred_start")),
        ("Programmes", programmes),
        ("Notes", record.get("notes")),
        ("Submitted at", record.get("submitted_at")),
    ]
    subject = f"Corporate training request: {record.get('company_name', '')}"
    text = "New corporate training request from the AfriCloud Institute website.\n\n" + format_fields(rows)
    html = _staff_notice_html(
        site,
        "Corporate training",
        record.get("company_name", "Corporate request"),
        "A company submitted a training request on the website.",
        rows,
        subject,
    )
    return send_inbox_email(subject, text, reply_to=record.get("email"), html=html)


def _send_smtp(recipient, subject, text, html=None, reply_to=None):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = sender_email()

    if not user or not password or not sender:
        logger.error("SMTP is not configured; email was not sent: %s", subject)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"AfriCloud Institute <{sender}>"
    message["To"] = recipient
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(text or "")
    if html:
        message.add_alternative(html, subtype="html")

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


def _send_gmail_webhook(recipient, subject, text, html=None, reply_to=None):
    url = os.environ.get("GMAIL_WEBHOOK_URL", "").strip()
    secret = os.environ.get("GMAIL_WEBHOOK_SECRET", "").strip()
    if not url or not secret:
        return False

    payload = json.dumps(
        {
            "secret": secret,
            "to": recipient,
            "subject": subject,
            "text": text or "",
            "html": html or text or "",
            "reply_to": reply_to or inbox_email(),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
        if result.get("ok") is True:
            logger.info("Gmail webhook email sent to %s: %s", recipient, subject)
            return True
        logger.error("Gmail webhook rejected email: %s %s", subject, result)
        return False
    except urllib.error.HTTPError as error:
        logger.error("Gmail webhook HTTP error: %s %s", error.code, error.read()[:500])
        return False
    except Exception:
        logger.exception("Failed to send Gmail webhook email: %s", subject)
        return False


def format_fields(fields):
    lines = []
    for label, value in fields:
        text = value if value else "—"
        if isinstance(text, list):
            text = ", ".join(text) if text else "—"
        lines.append(f"{label}: {text}")
    return "\n".join(lines)

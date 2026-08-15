import json
from calendar import monthrange
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock

_CONTENT_DIR = Path(__file__).parent / "content"
_SUBMISSIONS_DIR = Path(__file__).parent / "submissions"
_WRITE_LOCK = Lock()


def _load_json(filename):
    """Load editable site content from app/content/*.json."""
    with open(_CONTENT_DIR / filename, encoding="utf-8") as handle:
        return json.load(handle)


def _add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _format_date(value):
    return value.strftime("%B ") + str(value.day) + value.strftime(", %Y")


def _next_intake(anchor, cadence, today):
    start = anchor
    while start < today:
        start = _add_months(start, cadence)
    return start


def _enrich_bootcamp(course, today=None):
    """Compute the current/next cohort from an ISO start date so listings stay current."""
    today = today or date.today()
    item = deepcopy(course)
    starts_on = item.get("starts_on")
    if not starts_on:
        item.setdefault("status", "open")
        item.setdefault("status_label", "Applications open")
        return item

    anchor = date.fromisoformat(starts_on)
    duration_months = int(item.get("duration_months") or 6)
    cadence = int(item.get("intake_every_months") or duration_months)
    next_start = _next_intake(anchor, cadence, today)
    previous_start = _add_months(next_start, -cadence)
    previous_end = _add_months(previous_start, duration_months)
    in_session = previous_start >= anchor and previous_start < today <= previous_end

    days_until = (next_start - today).days
    if days_until == 0:
        status = "open"
        status_label = "Starts today"
    elif days_until <= 21:
        status = "open"
        status_label = "Starting soon"
    elif in_session:
        status = "in_session"
        status_label = "Cohort in session"
    else:
        status = "open"
        status_label = "Applications open"

    item["starts_on"] = next_start.isoformat()
    item["start_date"] = _format_date(next_start)
    item["status"] = status
    item["status_label"] = status_label
    item["in_session"] = in_session
    if in_session:
        item["current_end"] = _format_date(previous_end)
    return item


def get_courses_page():
    data = _load_json("bootcamps.json")
    if isinstance(data, list):
        return {
            "kicker": "Bootcamps",
            "title": "Professional training programmes",
            "lead": "Industry-relevant skills, instructor-led teaching, and hands-on projects.",
            "payment_note": "Flexible monthly payment plans available. Terms & conditions apply.",
            "cta_title": "Ready for the next cohort?",
            "cta_text": "Apply for a programme, then stay connected through email, phone, and the cohort WhatsApp group once you are admitted.",
            "programmes": data,
        }
    return data


def get_bootcamps():
    programmes = [_enrich_bootcamp(item) for item in get_courses_page().get("programmes", [])]
    programmes.sort(key=lambda item: item.get("starts_on") or "")
    return programmes


def get_featured_bootcamps(limit=4):
    return get_bootcamps()[:limit]


def get_founders():
    return _load_json("founders.json")


def get_site():
    return _load_json("site.json")


def get_faqs():
    return _load_json("faq.json")


def get_security_statement():
    return _load_json("security.json")


def get_home():
    return _load_json("home.json")


def get_apply_options():
    return _load_json("apply.json")


def get_testimonials():
    return _load_json("testimonials.json")


def get_corporate():
    return _load_json("corporate.json")


def get_legal():
    return _load_json("legal.json")


def get_legal_policy(slug):
    for policy in get_legal().get("policies", []):
        if policy.get("slug") == slug:
            return policy
    return None


def get_bootcamp(programme_id):
    for course in get_bootcamps():
        if course.get("id") == programme_id:
            return course
    return None


def save_submission(filename, record):
    _SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = _SUBMISSIONS_DIR / filename
    with _WRITE_LOCK:
        records = []
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                records = json.load(handle)
        records.append(record)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(records, handle, indent=2, ensure_ascii=False)


def save_application(record):
    save_submission("applications.json", record)


def save_corporate_enquiry(record):
    save_submission("corporate.json", record)


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

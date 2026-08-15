import re

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
from io import BytesIO

from app.pdf import build_legal_pdf
from app.data import (
    get_apply_options,
    get_bootcamp,
    get_bootcamps,
    get_corporate,
    get_courses_page,
    get_faqs,
    get_featured_bootcamps,
    get_founders,
    get_home,
    get_legal,
    get_legal_policy,
    get_security_statement,
    get_site,
    get_testimonials,
    save_application,
    save_contact_message,
    save_corporate_enquiry,
    utc_now_iso,
)
from app.mail import format_fields, send_inbox_email

main = Blueprint("main", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FIELD_LIMITS = {
    "full_name": 120,
    "email": 200,
    "phone": 40,
    "programme": 80,
    "city": 80,
    "experience": 80,
    "motivation": 2000,
}
_CONTACT_LIMITS = {
    "full_name": 120,
    "email": 200,
    "phone": 40,
    "message": 2000,
}


def _clean(value, limit):
    return (value or "").strip()[:limit]


def _deliver_inbox_email(subject, body, reply_to=None):
    sent = send_inbox_email(subject, body, reply_to=reply_to)
    if not sent:
        session["outbound_mail"] = {
            "subject": subject,
            "body": body,
            "reply_to": reply_to or "",
        }
    return sent


@main.route("/")
def home():
    return render_template(
        "index.html",
        home=get_home(),
        featured_courses=get_featured_bootcamps(),
        testimonials=get_testimonials(),
    )


@main.route("/courses")
def course_list():
    return render_template(
        "courses.html",
        courses=get_bootcamps(),
        page=get_courses_page(),
    )


@main.route("/about")
def about():
    return render_template("about.html", founders=get_founders())


@main.route("/contact", methods=["GET", "POST"])
def contact():
    form = {key: "" for key in _CONTACT_LIMITS}

    if request.method == "POST":
        form = {key: _clean(request.form.get(key), limit) for key, limit in _CONTACT_LIMITS.items()}
        errors = []
        if len(form["full_name"]) < 2:
            errors.append("Please enter your name.")
        if not _EMAIL_RE.match(form["email"]):
            errors.append("Please enter a valid email address.")
        if len(form["message"]) < 8:
            errors.append("Please write a short message.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            record = {
                "submitted_at": utc_now_iso(),
                "full_name": form["full_name"],
                "email": form["email"],
                "phone": form["phone"],
                "message": form["message"],
            }
            save_contact_message(record)
            _deliver_inbox_email(
                subject=f"Website enquiry from {form['full_name']}",
                body="New contact message from the AfriCloud Institute website.\n\n"
                + format_fields(
                    [
                        ("Name", record["full_name"]),
                        ("Email", record["email"]),
                        ("Phone", record["phone"]),
                        ("Message", record["message"]),
                        ("Submitted at", record["submitted_at"]),
                    ]
                ),
                reply_to=form["email"],
            )
            flash("Thank you. Your message has been received. We will reply by email or phone.", "success")
            return redirect(url_for("main.contact"))

    return render_template("contact.html", form=form)


@main.route("/faq")
def faq():
    return render_template("faq.html", faqs=get_faqs())


@main.route("/information-security")
def information_security():
    return render_template(
        "security.html",
        statement=get_security_statement(),
        legal=get_legal(),
    )


@main.route("/legal")
def legal():
    return render_template("legal.html", legal=get_legal())


@main.route("/legal/download")
def legal_download():
    pdf_bytes = build_legal_pdf(get_site(), get_legal(), get_security_statement())
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="AfriCloud-Institute-Legal-Policies.pdf",
    )


@main.route("/legal/<slug>")
def legal_policy(slug):
    policy = get_legal_policy(slug)
    if not policy:
        abort(404)
    return render_template(
        "legal_policy.html",
        legal=get_legal(),
        policy=policy,
    )


@main.route("/apply", methods=["GET", "POST"])
def apply():
    courses = get_bootcamps()
    selected = request.values.get("programme", "").strip()
    form = {
        "full_name": "",
        "email": "",
        "phone": "",
        "programme": selected if get_bootcamp(selected) else "",
        "city": "",
        "experience": "",
        "motivation": "",
    }

    if request.method == "POST":
        form = {key: _clean(request.form.get(key), limit) for key, limit in _FIELD_LIMITS.items()}
        errors = []

        if len(form["full_name"]) < 2:
            errors.append("Please enter your full name.")
        if not _EMAIL_RE.match(form["email"]):
            errors.append("Please enter a valid email address.")
        if len(form["phone"]) < 7:
            errors.append("Please enter a working phone number.")
        if not get_bootcamp(form["programme"]):
            errors.append("Please select a programme.")
        if request.form.get("consent") != "yes":
            errors.append("Please confirm that we may process your application details.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            course = get_bootcamp(form["programme"])
            record = {
                    "submitted_at": utc_now_iso(),
                    "full_name": form["full_name"],
                    "email": form["email"],
                    "phone": form["phone"],
                    "programme_id": form["programme"],
                    "programme_title": course["title"],
                    "city": form["city"],
                    "experience": form["experience"],
                    "motivation": form["motivation"],
                }
            save_application(record)
            _deliver_inbox_email(
                subject=f"Programme application: {course['title']}",
                body="New application from the AfriCloud Institute website.\n\n"
                + format_fields(
                    [
                        ("Name", record["full_name"]),
                        ("Email", record["email"]),
                        ("Phone", record["phone"]),
                        ("City", record["city"]),
                        ("Programme", record["programme_title"]),
                        ("Experience", record["experience"]),
                        ("Motivation", record["motivation"]),
                        ("Submitted at", record["submitted_at"]),
                    ]
                ),
                reply_to=form["email"],
            )
            flash(
                "Thank you. Your application has been received. Our team will contact you by email or phone. If you have been admitted to a cohort, join the WhatsApp group from the success note on this page.",
                "success",
            )
            return redirect(url_for("main.apply", programme=form["programme"]))

    return render_template(
        "apply.html",
        courses=courses,
        form=form,
        experience_levels=get_apply_options().get("experience_levels", []),
    )


_CORPORATE_LIMITS = {
    "company_name": 160,
    "contact_name": 120,
    "job_title": 120,
    "email": 200,
    "phone": 40,
    "team_size": 40,
    "preferred_start": 80,
    "notes": 2000,
}


@main.route("/corporate", methods=["GET", "POST"])
def corporate():
    courses = get_bootcamps()
    form = {key: "" for key in _CORPORATE_LIMITS}
    selected_programmes = []

    if request.method == "POST":
        form = {key: _clean(request.form.get(key), limit) for key, limit in _CORPORATE_LIMITS.items()}
        selected_programmes = [item for item in request.form.getlist("programmes") if get_bootcamp(item)]
        errors = []
        if len(form["company_name"]) < 2:
            errors.append("Please enter the company name.")
        if len(form["contact_name"]) < 2:
            errors.append("Please enter the contact person's name.")
        if not _EMAIL_RE.match(form["email"]):
            errors.append("Please enter a valid work email address.")
        if len(form["phone"]) < 7:
            errors.append("Please enter a working phone number.")
        if not selected_programmes:
            errors.append("Please select at least one programme.")
        if request.form.get("consent") != "yes":
            errors.append("Please agree to the Privacy Policy and Terms.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            record = {
                    "submitted_at": utc_now_iso(),
                    "company_name": form["company_name"],
                    "contact_name": form["contact_name"],
                    "job_title": form["job_title"],
                    "email": form["email"],
                    "phone": form["phone"],
                    "team_size": form["team_size"],
                    "preferred_start": form["preferred_start"],
                    "programmes": [
                        get_bootcamp(item)["title"] for item in selected_programmes
                    ],
                    "notes": form["notes"],
                }
            save_corporate_enquiry(record)
            _deliver_inbox_email(
                subject=f"Corporate training request: {form['company_name']}",
                body="New corporate training request from the AfriCloud Institute website.\n\n"
                + format_fields(
                    [
                        ("Company", record["company_name"]),
                        ("Contact", record["contact_name"]),
                        ("Job title", record["job_title"]),
                        ("Email", record["email"]),
                        ("Phone", record["phone"]),
                        ("Team size", record["team_size"]),
                        ("Preferred start", record["preferred_start"]),
                        ("Programmes", record["programmes"]),
                        ("Notes", record["notes"]),
                        ("Submitted at", record["submitted_at"]),
                    ]
                ),
                reply_to=form["email"],
            )
            flash(
                "Thank you. We have received your corporate training request and will contact you with a proposed plan.",
                "success",
            )
            return redirect(url_for("main.corporate"))

    return render_template(
        "corporate.html",
        corporate=get_corporate(),
        courses=courses,
        form=form,
        selected_programmes=selected_programmes,
    )

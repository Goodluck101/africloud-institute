import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, session

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def create_app():
    secret_key = os.environ.get("SECRET_KEY", "").strip()
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and add a random key."
        )

    application = Flask(
        __name__,
        template_folder=str(_ROOT / "templates"),
        static_folder=str(_ROOT / "static"),
    )
    application.secret_key = secret_key
    application.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}

    from app.routes import main
    from app.data import get_site

    application.register_blueprint(main)

    @application.context_processor
    def inject_globals():
        return {
            "site": get_site(),
            "current_year": datetime.now().year,
            "outbound_mail": session.get("outbound_mail"),
        }

    @application.after_request
    def clear_outbound_mail(response):
        if request.method == "GET":
            session.pop("outbound_mail", None)
        return response

    return application


app = create_app()

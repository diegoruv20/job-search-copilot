import os
from pathlib import Path

from flask import Flask
from sqlalchemy import inspect, text

from models import db


def ensure_job_columns():
    existing = {column["name"] for column in inspect(db.engine).get_columns("jobs")}
    additions = {
        "first_published_date": "DATE",
        "posting_updated_date": "DATE",
        "linkedin_reposted_date": "DATE",
        "last_verified_date": "DATE",
        "freshness_source": "VARCHAR(120)",
        "freshness_confidence": "VARCHAR(20)",
    }
    for name, column_type in additions.items():
        if name not in existing:
            db.session.execute(text(f"ALTER TABLE jobs ADD COLUMN {name} {column_type}"))
    db.session.commit()


def create_app(test_config=None):
    app = Flask(__name__)
    default_database = Path(app.instance_path) / "applications.db"
    database_path = Path(
        os.environ.get("JOB_TRACKER_DATABASE_PATH", str(default_database))
    ).expanduser()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"timeout": 15}},
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(database_path.parent, exist_ok=True)
    db.init_app(app)

    from api import api_bp, backfill_sankey_history, ensure_sankey_baseline
    from views import views_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    with app.app_context():
        db.create_all()
        ensure_job_columns()
        job_columns = {
            column["name"] for column in inspect(db.engine).get_columns("jobs")
        }
        sankey_columns = {
            "applied_date",
            "archived",
            "created_at",
            "not_fit_category",
            "stage",
            "status",
        }
        if sankey_columns.issubset(job_columns):
            ensure_sankey_baseline()
            backfill_sankey_history()

    return app


if __name__ == "__main__":
    debug = os.environ.get("JOB_TRACKER_DEBUG", "").lower() in {"1", "true", "yes"}
    host = os.environ.get("JOB_TRACKER_HOST", "127.0.0.1")
    port = int(os.environ.get("JOB_TRACKER_PORT", "5001"))
    create_app().run(debug=debug, host=host, port=port)

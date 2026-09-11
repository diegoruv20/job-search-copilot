import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app

from models import Job, SankeySnapshot, StatusHistory, db
from services import create_job


EXPORT_VERSION = 1
DATE_FIELDS = {
    "next_action_date",
    "applied_date",
    "first_published_date",
    "posting_updated_date",
    "linkedin_reposted_date",
    "last_verified_date",
}
DATETIME_FIELDS = {"created_at", "updated_at"}


def database_path():
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    prefix = "sqlite:///"
    if not uri.startswith(prefix) or uri.endswith(":memory:"):
        raise ValueError("Data portability currently supports file-backed SQLite only")
    return Path(uri[len(prefix) :]).resolve()


def _timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _serialize_model(item):
    result = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result


def _parse_record(record, date_fields=(), datetime_fields=()):
    parsed = dict(record)
    for field in date_fields:
        if parsed.get(field):
            parsed[field] = date.fromisoformat(parsed[field])
    for field in datetime_fields:
        if parsed.get(field):
            parsed[field] = datetime.fromisoformat(parsed[field])
    return parsed


def backup_database(destination=None):
    source_path = database_path()
    destination_path = (
        Path(destination).expanduser().resolve()
        if destination
        else Path(current_app.root_path)
        / "backups"
        / f"job-tracker-{_timestamp()}.db"
    )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source_path)) as source, closing(
        sqlite3.connect(destination_path)
    ) as target:
        source.backup(target)
    return destination_path


def restore_database(source, confirm=False):
    if not confirm:
        raise ValueError("Set confirm=True to restore over the current database")
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Backup does not exist: {source_path}")

    safety_backup = backup_database()
    target_path = database_path()
    db.session.remove()
    db.engine.dispose()
    with closing(sqlite3.connect(source_path)) as backup, closing(
        sqlite3.connect(target_path)
    ) as target:
        backup.backup(target)
    return {"restored_from": source_path, "safety_backup": safety_backup}


def export_json(destination=None):
    destination_path = (
        Path(destination).expanduser().resolve()
        if destination
        else Path(current_app.root_path)
        / "exports"
        / f"job-tracker-{_timestamp()}.json"
    )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now().isoformat(),
        "jobs": [_serialize_model(item) for item in Job.query.order_by(Job.id)],
        "status_history": [
            _serialize_model(item) for item in StatusHistory.query.order_by(StatusHistory.id)
        ],
        "sankey_snapshots": [
            _serialize_model(item)
            for item in SankeySnapshot.query.order_by(SankeySnapshot.id)
        ],
    }
    destination_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination_path


def import_json(source, replace=False):
    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise ValueError(f"Import file does not exist: {source_path}")
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if payload.get("version") != EXPORT_VERSION:
        raise ValueError(f"Unsupported export version: {payload.get('version')}")
    if not isinstance(payload.get("jobs"), list):
        raise ValueError("Import file must contain a jobs list")
    for record in payload["jobs"]:
        if not record.get("company") or not record.get("role"):
            raise ValueError("Every imported job requires company and role")
    if Job.query.count() and not replace:
        raise ValueError("Tracker is not empty; set replace=True to import")

    has_jobs = bool(Job.query.count())
    safety_backup = backup_database() if has_jobs else None
    if replace or not has_jobs:
        SankeySnapshot.query.delete()
        StatusHistory.query.delete()
        Job.query.delete()
        db.session.flush()

    for record in payload["jobs"]:
        db.session.add(
            Job(**_parse_record(record, DATE_FIELDS, DATETIME_FIELDS))
        )
    db.session.flush()
    for record in payload.get("status_history", []):
        db.session.add(
            StatusHistory(**_parse_record(record, datetime_fields={"created_at"}))
        )
    for record in payload.get("sankey_snapshots", []):
        db.session.add(
            SankeySnapshot(**_parse_record(record, datetime_fields={"created_at"}))
        )
    db.session.commit()
    return {"jobs": len(payload["jobs"]), "safety_backup": safety_backup}


def load_demo(replace=False):
    if Job.query.count() and not replace:
        raise ValueError("Tracker is not empty; use replace=True to load demo data")
    safety_backup = backup_database() if Job.query.count() else None
    if replace:
        SankeySnapshot.query.delete()
        StatusHistory.query.delete()
        Job.query.delete()
        db.session.commit()

    demo_path = Path(current_app.root_path) / "data" / "demo_jobs.json"
    records = json.loads(demo_path.read_text(encoding="utf-8"))
    today = date.today()
    for record in records:
        for source, target, direction in (
            ("next_action_days_from_now", "next_action_date", 1),
            ("applied_days_ago", "applied_date", -1),
            ("first_published_days_ago", "first_published_date", -1),
            ("last_verified_days_ago", "last_verified_date", -1),
        ):
            if source in record:
                record[target] = (
                    today + timedelta(days=direction * record.pop(source))
                ).isoformat()
    jobs = [create_job(record) for record in records]
    return {"jobs": [job.to_dict() for job in jobs], "safety_backup": safety_backup}

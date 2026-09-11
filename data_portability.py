import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app

from models import Job, SankeySnapshot, StatusHistory, db
from services import EDITABLE_FIELDS, apply_payload, create_job


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


def _validate_model_record(record, model, date_fields=(), datetime_fields=()):
    if not isinstance(record, dict):
        raise ValueError(f"Every {model.__tablename__} record must be an object")
    columns = {column.name for column in model.__table__.columns}
    unknown = set(record) - columns
    if unknown:
        raise ValueError(
            f"Unknown {model.__tablename__} fields: {', '.join(sorted(unknown))}"
        )
    return _parse_record(record, date_fields, datetime_fields)


def _validate_import_payload(payload):
    if payload.get("version") != EXPORT_VERSION:
        raise ValueError(f"Unsupported export version: {payload.get('version')}")
    if not isinstance(payload.get("jobs"), list):
        raise ValueError("Import file must contain a jobs list")
    if not isinstance(payload.get("status_history", []), list):
        raise ValueError("status_history must be a list")
    if not isinstance(payload.get("sankey_snapshots", []), list):
        raise ValueError("sankey_snapshots must be a list")

    jobs = []
    for record in payload["jobs"]:
        if not isinstance(record, dict) or not record.get("company") or not record.get(
            "role"
        ):
            raise ValueError("Every imported job requires company and role")
        parsed = _validate_model_record(record, Job, DATE_FIELDS, DATETIME_FIELDS)
        candidate = Job(**parsed)
        apply_payload(
            candidate,
            {field: record[field] for field in EDITABLE_FIELDS if field in record},
        )
        jobs.append(parsed)

    job_ids = {record.get("id") for record in jobs}
    history = [
        _validate_model_record(
            record, StatusHistory, datetime_fields={"created_at"}
        )
        for record in payload.get("status_history", [])
    ]
    if any(record.get("job_id") not in job_ids for record in history):
        raise ValueError("Every status history record must reference an imported job")

    snapshots = [
        _validate_model_record(
            record, SankeySnapshot, datetime_fields={"created_at"}
        )
        for record in payload.get("sankey_snapshots", [])
    ]
    for snapshot in snapshots:
        try:
            data = json.loads(snapshot.get("data_json", ""))
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Every Sankey snapshot requires valid JSON data") from exc
        if not isinstance(data, dict) or not isinstance(
            data.get("nodes"), list
        ) or not isinstance(
            data.get("links"), list
        ):
            raise ValueError("Every Sankey snapshot requires nodes and links lists")
    return jobs, history, snapshots


def _validate_sqlite_backup(source_path):
    try:
        with closing(sqlite3.connect(source_path)) as source:
            integrity = source.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("Backup failed SQLite integrity validation")
            tables = {
                row[0]
                for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
    except sqlite3.DatabaseError as exc:
        raise ValueError("Restore source is not a valid SQLite database") from exc
    required = {"jobs", "status_history", "sankey_snapshots"}
    if not required.issubset(tables):
        missing = ", ".join(sorted(required - tables))
        raise ValueError(f"Restore source is missing tracker tables: {missing}")


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
    _validate_sqlite_backup(source_path)

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
    jobs, history, snapshots = _validate_import_payload(payload)
    if Job.query.count() and not replace:
        raise ValueError("Tracker is not empty; set replace=True to import")

    has_jobs = bool(Job.query.count())
    safety_backup = backup_database() if has_jobs else None
    if replace or not has_jobs:
        SankeySnapshot.query.delete()
        StatusHistory.query.delete()
        Job.query.delete()
        db.session.flush()

    for record in jobs:
        db.session.add(Job(**record))
    db.session.flush()
    for record in history:
        db.session.add(StatusHistory(**record))
    for record in snapshots:
        db.session.add(SankeySnapshot(**record))
    db.session.commit()
    return {"jobs": len(jobs), "safety_backup": safety_backup}


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

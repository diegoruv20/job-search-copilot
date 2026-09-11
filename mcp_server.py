import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from flask import current_app
from mcp.server import MCPServer

from app import create_app
from data_portability import (
    backup_database,
    export_json,
    import_json,
    load_demo,
    restore_database,
)
from services import (
    TrackerNotFoundError,
    TrackerValidationError,
    create_job,
    get_job,
    history,
    list_jobs,
    metadata,
    recommendations,
    stats,
    update_job,
)
from workspace import profile_status as get_profile_status


ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "runtime"
PID_PATH = RUNTIME_DIR / "dashboard.pid"
LOG_PATH = RUNTIME_DIR / "dashboard.log"
HOST = os.environ.get("JOB_TRACKER_HOST", "127.0.0.1")
PORT = int(os.environ.get("JOB_TRACKER_PORT", "5050"))
DASHBOARD_URL = f"http://{HOST}:{PORT}"
_managed_processes: dict[int, subprocess.Popen] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = MCPServer(
    "job-search-copilot",
    title="Job Search Copilot",
    description="Local tools for a private job application tracker.",
    instructions=(
        "Inspect the tracker before making recommendations. Use tracker tools for "
        "state changes and Playwright for external job sites or dashboard UI tests. "
        "Never submit applications or send outreach without explicit user approval."
    ),
)


def _with_app(callback):
    app = create_app()
    with app.app_context():
        try:
            return callback()
        finally:
            from models import db

            db.session.remove()
            db.engine.dispose()


def _tool_result(callback):
    try:
        return _with_app(callback)
    except (TrackerValidationError, TrackerNotFoundError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def _dashboard_health(timeout=0.75):
    try:
        with urlopen(f"{DASHBOARD_URL}/api/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and payload.get("status") == "ok"
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return False


def _read_pid():
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, TypeError, ValueError):
        return None


def _process_exists(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@mcp.resource("tracker://metadata")
def tracker_metadata() -> str:
    """Read valid tracker statuses, tiers, and classification values."""
    return json.dumps(metadata(), indent=2)


@mcp.resource("tracker://workflow")
def tracker_workflow() -> str:
    """Read the safe operating rules for the local tracker."""
    return (
        "Inspect live tracker state before recommending work. Verify job postings "
        "on the official employer or ATS page with Playwright. Keep original, "
        "updated, and reposted dates separate. Record only evidence-backed fit and "
        "gaps. Do not submit applications, upload resumes, or send messages without "
        "explicit user approval."
    )


@mcp.resource("tracker://profile-status")
def tracker_profile_status_resource() -> str:
    """Read whether private personalization files are ready."""
    return json.dumps(get_profile_status(), indent=2)


@mcp.resource("tracker://profile-onboarding")
def tracker_profile_onboarding_resource() -> str:
    """Read the systematic guided career interview workflow."""
    return (ROOT / "docs" / "profile-onboarding.md").read_text(encoding="utf-8")


@mcp.tool()
def tracker_initialize() -> dict[str, Any]:
    """Create or upgrade the local database without adding jobs."""
    return _tool_result(
        lambda: {
            "ok": True,
            "database_uri": current_app.config["SQLALCHEMY_DATABASE_URI"],
            "stats": stats(),
        }
    )


@mcp.tool()
def profile_status() -> dict[str, Any]:
    """Check guided-interview status, unresolved follow-ups, and the next action."""
    return {"ok": True, **get_profile_status()}


@mcp.tool()
def dashboard_status() -> dict[str, Any]:
    """Report the local dashboard URL, health, and managed process ID."""
    pid = _read_pid()
    healthy = _dashboard_health()
    return {
        "ok": True,
        "url": DASHBOARD_URL,
        "healthy": healthy,
        "pid": pid if pid and _process_exists(pid) else None,
    }


@mcp.tool()
def dashboard_start() -> dict[str, Any]:
    """Start the localhost dashboard if it is not already healthy."""
    if _dashboard_health():
        return dashboard_status()

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    existing_pid = _read_pid()
    if existing_pid and not _process_exists(existing_pid):
        PID_PATH.unlink(missing_ok=True)

    environment = os.environ.copy()
    environment.update(
        {
            "JOB_TRACKER_HOST": HOST,
            "JOB_TRACKER_PORT": str(PORT),
            "JOB_TRACKER_DEBUG": "false",
        }
    )
    creation_flags = (
        subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "app.py")],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
        )
    _managed_processes[process.pid] = process
    PID_PATH.write_text(str(process.pid), encoding="utf-8")

    for _ in range(40):
        if _dashboard_health():
            return dashboard_status()
        if process.poll() is not None:
            break
        time.sleep(0.1)

    return {
        "ok": False,
        "error": f"Dashboard did not become healthy. Check {LOG_PATH}.",
        "pid": process.pid,
        "url": DASHBOARD_URL,
    }


@mcp.tool()
def dashboard_stop(confirm: bool = False) -> dict[str, Any]:
    """Stop only the dashboard process recorded by this repository."""
    if not confirm:
        return {
            "ok": False,
            "error": "Set confirm=true to stop the managed dashboard process.",
        }

    pid = _read_pid()
    if not pid:
        return {"ok": True, "stopped": False, "message": "No managed process found."}
    if not _process_exists(pid):
        PID_PATH.unlink(missing_ok=True)
        return {"ok": True, "stopped": False, "message": "Process was not running."}

    process = _managed_processes.get(pid)
    if process is not None:
        process.terminate()
    else:
        os.kill(pid, signal.SIGTERM)
    for _ in range(30):
        stopped = (
            process.poll() is not None if process is not None else not _process_exists(pid)
        )
        if stopped:
            process = _managed_processes.pop(pid, None)
            if process is not None and process.poll() is None:
                process.wait(timeout=1)
            PID_PATH.unlink(missing_ok=True)
            return {"ok": True, "stopped": True, "pid": pid}
        time.sleep(0.1)
    return {
        "ok": False,
        "error": "Managed dashboard did not stop within three seconds.",
        "pid": pid,
    }


@mcp.tool()
def job_list(
    search: str = "",
    status: str = "",
    tier: str = "",
    archive: str = "active",
) -> dict[str, Any]:
    """List jobs using the same filters and ordering as the dashboard."""
    return _tool_result(
        lambda: {
            "ok": True,
            "jobs": [
                job.to_dict()
                for job in list_jobs(
                    search=search, status=status, tier=tier, archive=archive
                )
            ],
        }
    )


@mcp.tool()
def job_get(job_id: int) -> dict[str, Any]:
    """Get one tracked job by ID."""
    return _tool_result(lambda: {"ok": True, "job": get_job(job_id).to_dict()})


@mcp.tool()
def job_create(
    company: str,
    role: str,
    status: str = "Researching",
    stage: str | None = None,
    url: str | None = None,
    location: str | None = None,
    compensation: str | None = None,
    fit_summary: str | None = None,
    decision: str | None = None,
    recommendation_tier: str = "Monitor",
    recommendation_rank: int | None = None,
    on_call: str | None = None,
    risk: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = None,
    first_published_date: str | None = None,
    posting_updated_date: str | None = None,
    linkedin_reposted_date: str | None = None,
    last_verified_date: str | None = None,
    freshness_source: str | None = None,
    freshness_confidence: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a job after official-posting verification and deduplication."""
    payload = {
        key: value
        for key, value in locals().items()
        if value is not None
    }
    return _tool_result(
        lambda: {"ok": True, "job": create_job(payload).to_dict()}
    )


@mcp.tool()
def job_update(
    job_id: int,
    status: str | None = None,
    stage: str | None = None,
    url: str | None = None,
    location: str | None = None,
    compensation: str | None = None,
    fit_summary: str | None = None,
    decision: str | None = None,
    not_fit_category: str | None = None,
    recommendation_tier: str | None = None,
    recommendation_rank: int | None = None,
    on_call: str | None = None,
    risk: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = None,
    applied_date: str | None = None,
    first_published_date: str | None = None,
    posting_updated_date: str | None = None,
    linkedin_reposted_date: str | None = None,
    last_verified_date: str | None = None,
    freshness_source: str | None = None,
    freshness_confidence: str | None = None,
    notes: str | None = None,
    archived: bool | None = None,
    status_note: str | None = None,
) -> dict[str, Any]:
    """Update a job through the tracker's validated lifecycle rules."""
    payload = {
        key: value
        for key, value in locals().items()
        if key != "job_id" and value is not None
    }
    return _tool_result(
        lambda: {"ok": True, "job": update_job(job_id, payload).to_dict()}
    )


@mcp.tool()
def application_record(
    job_id: int,
    applied_date: str | None = None,
    stage: str = "Application submitted",
    notes: str | None = None,
) -> dict[str, Any]:
    """Record a confirmed application submission; never submits an application."""
    payload = {
        "status": "Applied",
        "stage": stage,
        "applied_date": applied_date or date.today().isoformat(),
        "status_note": "Application submitted",
    }
    if notes is not None:
        payload["notes"] = notes
    return _tool_result(
        lambda: {"ok": True, "job": update_job(job_id, payload).to_dict()}
    )


@mcp.tool()
def outcome_record(
    job_id: int,
    status: str,
    stage: str,
    note: str,
    next_action: str | None = None,
    next_action_date: str | None = None,
) -> dict[str, Any]:
    """Record a confirmed interview-stage change, rejection, withdrawal, or offer."""
    allowed = {
        "Recruiter Screen",
        "Hiring Manager",
        "Technical Interview",
        "System Design",
        "Onsite",
        "Offer",
        "Rejected",
        "Withdrawn",
    }
    if status not in allowed:
        return {"ok": False, "error": f"Outcome status must be one of {sorted(allowed)}"}
    payload = {
        "status": status,
        "stage": stage,
        "status_note": note,
        "next_action": next_action,
        "next_action_date": next_action_date,
    }
    return _tool_result(
        lambda: {"ok": True, "job": update_job(job_id, payload).to_dict()}
    )


@mcp.tool()
def followups_due() -> dict[str, Any]:
    """List active jobs whose next action date is today or earlier."""
    return _tool_result(
        lambda: {
            "ok": True,
            "jobs": [
                job.to_dict()
                for job in list_jobs(archive="all")
                if job.follow_up_due
            ],
        }
    )


@mcp.tool()
def recommendations_get(limit: int = 8) -> dict[str, Any]:
    """Return the current prioritized application queue."""
    bounded_limit = min(max(limit, 1), 25)
    return _tool_result(
        lambda: {
            "ok": True,
            "jobs": [job.to_dict() for job in recommendations(bounded_limit)],
        }
    )


@mcp.tool()
def stats_get() -> dict[str, Any]:
    """Return current pipeline, follow-up, and freshness-conversion statistics."""
    return _tool_result(lambda: {"ok": True, "stats": stats()})


@mcp.tool()
def history_get(limit: int = 12) -> dict[str, Any]:
    """Return recent status transitions."""
    return _tool_result(
        lambda: {
            "ok": True,
            "history": [item.to_dict() for item in history(limit)],
        }
    )


@mcp.tool()
def tracker_demo_load(replace: bool = False) -> dict[str, Any]:
    """Load fictional demo jobs; replacement requires replace=true."""
    return _tool_result(lambda: {"ok": True, **load_demo(replace=replace)})


@mcp.tool()
def tracker_backup(destination: str | None = None) -> dict[str, Any]:
    """Create an online SQLite backup without stopping the dashboard."""
    return _tool_result(
        lambda: {"ok": True, "path": str(backup_database(destination))}
    )


@mcp.tool()
def tracker_export(destination: str | None = None) -> dict[str, Any]:
    """Export jobs, status history, and Sankey history to versioned JSON."""
    return _tool_result(lambda: {"ok": True, "path": str(export_json(destination))})


@mcp.tool()
def tracker_import(source: str, replace: bool = False) -> dict[str, Any]:
    """Import versioned tracker JSON; existing state requires replace=true."""
    return _tool_result(lambda: {"ok": True, **import_json(source, replace=replace)})


@mcp.tool()
def tracker_restore(source: str, confirm: bool = False) -> dict[str, Any]:
    """Restore a SQLite backup after creating a safety backup."""
    return _tool_result(
        lambda: {
            "ok": True,
            **restore_database(source, confirm=confirm),
        }
    )


if __name__ == "__main__":
    mcp.run()

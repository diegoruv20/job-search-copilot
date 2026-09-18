import json
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from sqlalchemy import and_, case, func, or_

from .models import (
    FRESHNESS_BUCKETS,
    Job,
    SankeySnapshot,
    StatusHistory,
    db,
    freshness_bucket,
)


STATUSES = [
    "Researching",
    "Referral Prep",
    "Preparing",
    "Ready to Apply",
    "Applied",
    "Recruiter Screen",
    "Hiring Manager",
    "Technical Interview",
    "System Design",
    "Onsite",
    "Offer",
    "Hold",
    "Not a Fit",
    "Rejected",
    "Withdrawn",
]

ACTIVE_APPLICATION_STATUSES = {
    "Applied",
    "Recruiter Screen",
    "Hiring Manager",
    "Technical Interview",
    "System Design",
    "Onsite",
    "Offer",
}

TERMINAL_APPLICATION_STATUSES = {"Rejected", "Withdrawn"}
APPLIED_STATUSES = ACTIVE_APPLICATION_STATUSES | TERMINAL_APPLICATION_STATUSES
NON_APPLICATION_TERMINAL_STATUSES = {"Not a Fit"}
RECOMMENDATION_EXCLUDED_STATUSES = (
    APPLIED_STATUSES | NON_APPLICATION_TERMINAL_STATUSES
)
CURRENT_PURSUIT_STATUSES = {
    "Recruiter Screen",
    "Hiring Manager",
    "Technical Interview",
    "System Design",
    "Onsite",
}

RECRUITER_ACTIVITY_PATTERNS = (
    re.compile(
        r"\b(?:recruiter|talent acquisition|hiring manager)\b.{0,100}"
        r"\b(?:responded|replied|contacted|reached out|invited|asked|requested)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:responded|replied|contacted|reached out|invited|asked|requested)\b"
        r".{0,100}\b(?:recruiter|talent acquisition|hiring manager)\b",
        re.IGNORECASE,
    ),
)

RECRUITER_EVENT_PATTERNS = (
    re.compile(
        r"\b(?:recruiter|talent acquisition|hiring manager)\b.{0,100}"
        r"\b(?:call|screen|chat|conversation|interview|follow-up|follow up)\b"
        r".{0,100}\b(?:scheduled|confirmed|booked|invited|requested)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:scheduled|confirmed|booked|invited|requested)\b.{0,100}"
        r"\b(?:recruiter|talent acquisition|hiring manager)\b.{0,100}"
        r"\b(?:call|screen|chat|conversation|interview|follow-up|follow up)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bschedule\b.{0,100}\b(?:recruiter|talent acquisition|hiring manager)\b"
        r".{0,100}\b(?:call|screen|chat|conversation|interview|follow-up|follow up)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:recruiter|talent acquisition|hiring manager)\b.{0,100}"
        r"\b(?:invited|requested|asked)\b.{0,100}"
        r"\b(?:schedule|call|screen|chat|conversation|interview|follow-up|follow up)\b",
        re.IGNORECASE,
    ),
)

TIERS = ["Apply Next", "Prepare Soon", "Conditional", "Monitor", "Active Application"]
FRESHNESS_CONFIDENCE = ["High", "Medium", "Low"]

NOT_FIT_CATEGORIES = [
    "Required experience / seniority",
    "Required technology stack",
    "Role specialization mismatch",
    "Work-life / on-call",
    "Location / office requirement",
    "Compensation insufficient",
    "Posting stale / high competition",
    "Superseded by stronger opportunity",
    "Excluded company / industry",
    "Other documented reason",
]

EDITABLE_FIELDS = {
    "company",
    "role",
    "status",
    "stage",
    "url",
    "location",
    "compensation",
    "fit_summary",
    "decision",
    "not_fit_category",
    "recommendation_tier",
    "recommendation_rank",
    "on_call",
    "risk",
    "next_action",
    "next_action_date",
    "applied_date",
    "first_published_date",
    "posting_updated_date",
    "linkedin_reposted_date",
    "last_verified_date",
    "freshness_source",
    "freshness_confidence",
    "notes",
    "archived",
}


class TrackerValidationError(ValueError):
    pass


class TrackerNotFoundError(LookupError):
    pass


def metadata():
    return {
        "statuses": STATUSES,
        "tiers": TIERS,
        "not_fit_categories": NOT_FIT_CATEGORIES,
        "freshness_confidence": FRESHNESS_CONFIDENCE,
    }


def tracker_revision():
    job_count, job_id_total, latest_job_update = db.session.query(
        func.count(Job.id),
        func.coalesce(func.sum(Job.id), 0),
        func.max(Job.updated_at),
    ).one()
    history_count, latest_history_id = db.session.query(
        func.count(StatusHistory.id),
        func.coalesce(func.max(StatusHistory.id), 0),
    ).one()
    snapshot_count, latest_snapshot_id = db.session.query(
        func.count(SankeySnapshot.id),
        func.coalesce(func.max(SankeySnapshot.id), 0),
    ).one()
    latest_update = (
        latest_job_update.isoformat(timespec="microseconds")
        if latest_job_update
        else ""
    )
    return {
        "revision": ":".join(
            str(value)
            for value in (
                job_count,
                job_id_total,
                latest_update,
                history_count,
                latest_history_id,
                snapshot_count,
                latest_snapshot_id,
            )
        )
    }


def parse_date(value, field):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise TrackerValidationError(
            f"{field} must be an ISO date (YYYY-MM-DD)"
        ) from exc


def apply_payload(job, payload):
    for field in EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field in {
            "next_action_date",
            "applied_date",
            "first_published_date",
            "posting_updated_date",
            "linkedin_reposted_date",
            "last_verified_date",
        }:
            value = parse_date(value, field)
        elif field == "archived":
            if not isinstance(value, bool):
                raise TrackerValidationError("archived must be a boolean")
        elif field == "recommendation_rank":
            try:
                value = int(value) if value not in (None, "") else None
            except (TypeError, ValueError) as exc:
                raise TrackerValidationError(
                    "recommendation_rank must be an integer"
                ) from exc
            if value is not None and value < 1:
                raise TrackerValidationError(
                    "recommendation_rank must be greater than zero"
                )
        elif isinstance(value, str):
            value = value.strip() or None
        if field == "url" and value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise TrackerValidationError("URL must start with http:// or https://")
        setattr(job, field, value)

    if not job.company or not job.role:
        raise TrackerValidationError("Company and role are required")
    if job.status not in STATUSES:
        raise TrackerValidationError("Invalid status")
    if job.recommendation_tier not in TIERS:
        raise TrackerValidationError("Invalid recommendation tier")
    if job.status == "Not a Fit" and not job.decision:
        raise TrackerValidationError("A decision reason is required for Not a Fit jobs")
    if job.status == "Not a Fit" and not job.not_fit_category:
        raise TrackerValidationError("A primary Not a Fit category is required")
    if job.not_fit_category and job.not_fit_category not in NOT_FIT_CATEGORIES:
        raise TrackerValidationError("Invalid Not a Fit category")
    if (
        job.freshness_confidence
        and job.freshness_confidence not in FRESHNESS_CONFIDENCE
    ):
        raise TrackerValidationError("Invalid freshness confidence")


def sync_application_state(job, payload, status_changed=False):
    if job.status in ACTIVE_APPLICATION_STATUSES:
        job.recommendation_tier = "Active Application"
        job.recommendation_rank = None
    elif (
        job.status in TERMINAL_APPLICATION_STATUSES
        and job.recommendation_tier == "Active Application"
    ):
        job.recommendation_tier = "Monitor"
        job.recommendation_rank = None
    elif job.status in NON_APPLICATION_TERMINAL_STATUSES:
        job.recommendation_tier = "Monitor"
        job.recommendation_rank = None
        job.next_action_date = None

    if job.status == "Applied" and status_changed and "stage" not in payload:
        job.stage = "Application submitted"
    elif (
        job.status in NON_APPLICATION_TERMINAL_STATUSES
        and status_changed
        and "stage" not in payload
    ):
        job.stage = "Not selected for application"


def build_sankey_data(jobs=None):
    if jobs is None:
        jobs = Job.query.filter(
            or_(Job.archived.is_(False), Job.applied_date.is_not(None))
        ).all()
    initial_screen_statuses = {"Recruiter Screen", "Hiring Manager"}
    technical_interview_statuses = {
        "Technical Interview",
        "System Design",
    }
    interview_statuses = (
        initial_screen_statuses
        | technical_interview_statuses
        | {
            "Onsite",
            "Offer",
        }
    )
    final_statuses = {"Onsite", "Offer"}

    def reached_status(job, statuses):
        if job.status in statuses:
            return True
        return any(
            item.new_status in statuses
            for item in getattr(job, "histories", [])
        )

    def outcome_phase(job):
        stage = (job.stage or "").lower()
        if any(marker in stage for marker in ("final", "onsite")):
            return "final"
        if any(
            marker in stage
            for marker in (
                "technical",
                "coding",
                "system design",
            )
        ):
            return "technical"
        if any(marker in stage for marker in ("recruiter", "hiring manager")):
            return "initial"
        if reached_status(job, final_statuses):
            return "final"
        if reached_status(job, technical_interview_statuses):
            return "technical"
        if reached_status(job, initial_screen_statuses):
            return "initial"
        if "interview" in stage:
            return "technical"
        return "resume"

    links = {}

    def add(source, target, value=1):
        if value:
            links[(source, target)] = links.get((source, target), 0) + value

    for job in jobs:
        if job.applied_date:
            add("Tracked roles", "Applied")
            add("Applied", "Resume review")
            phase = outcome_phase(job)

            if job.status == "Rejected" and phase == "resume":
                add("Resume review", "Rejected at resume review")
                continue
            if job.status == "Withdrawn":
                add("Resume review", "Withdrawn")
                continue
            if job.status == "Applied" or (
                job.status not in {"Rejected", "Withdrawn"}
                and not reached_status(job, interview_statuses)
            ):
                add("Resume review", "No response yet")
                continue

            add("Resume review", "Initial screen")

            if job.status == "Rejected" and phase == "initial":
                add("Initial screen", "Rejected during interviews")
                continue
            if phase == "initial":
                add("Initial screen", "Active initial screen")
                continue

            add("Initial screen", "Technical interview")

            if job.status == "Rejected" and phase == "technical":
                add("Technical interview", "Rejected during interviews")
                continue
            if phase == "technical":
                add("Technical interview", "Active technical interview")
                continue

            add("Technical interview", "Final / onsite")
            if job.status == "Rejected":
                add("Final / onsite", "Rejected after final interview")
            elif job.status == "Offer":
                add("Final / onsite", "Offer")
            else:
                add("Final / onsite", "Final interview active")
        else:
            add("Tracked roles", "Not applied")
            if job.status == "Ready to Apply":
                add("Not applied", "Ready to apply")
            elif job.status == "Not a Fit":
                add("Not applied", "Not a fit")
                add("Not a fit", job.not_fit_category or "Other documented reason")
            elif job.status == "Hold":
                add("Not applied", "On hold")
            elif job.status == "Referral Prep":
                add("Not applied", "Referral prep")
            else:
                add("Not applied", "Preparing")

    node_names = []
    for source, target in links:
        for name in (source, target):
            if name not in node_names:
                node_names.append(name)

    return {
        "nodes": [{"name": name} for name in node_names],
        "links": [
            {
                "source": node_names.index(source),
                "target": node_names.index(target),
                "value": value,
            }
            for (source, target), value in links.items()
        ],
    }


def record_sankey_snapshot(reason):
    data_json = json.dumps(build_sankey_data(), separators=(",", ":"), sort_keys=True)
    latest = SankeySnapshot.query.order_by(
        SankeySnapshot.created_at.desc(), SankeySnapshot.id.desc()
    ).first()
    if latest and latest.data_json == data_json:
        return None
    snapshot = SankeySnapshot(data_json=data_json, reason=reason)
    db.session.add(snapshot)
    return snapshot


def ensure_sankey_baseline():
    if SankeySnapshot.query.first() is None:
        record_sankey_snapshot("History tracking started")
        db.session.commit()


def backfill_sankey_history():
    if SankeySnapshot.query.filter(
        SankeySnapshot.reason.like("Estimated replay —%")
    ).first():
        return

    jobs = Job.query.order_by(Job.id).all()
    applied_dates = [job.applied_date for job in jobs if job.applied_date]
    if not applied_dates:
        return

    first_exact = SankeySnapshot.query.filter(
        ~SankeySnapshot.reason.like("Estimated replay —%")
    ).order_by(SankeySnapshot.created_at).first()
    last_estimated_date = (
        first_exact.created_at.date() - timedelta(days=1)
        if first_exact
        else date.today() - timedelta(days=1)
    )
    current_date = min(applied_dates)

    while current_date <= last_estimated_date:
        end_of_day = datetime.combine(current_date, time.max)
        historical_jobs = []
        for job in jobs:
            existed = job.created_at <= end_of_day
            was_applied = bool(job.applied_date and job.applied_date <= current_date)
            if not existed and not was_applied:
                continue

            status = "Applied" if was_applied else job.status
            transitions = sorted(job.histories, key=lambda item: item.created_at)
            applicable = [
                transition
                for transition in transitions
                if transition.created_at <= end_of_day
            ]
            if applicable:
                status = applicable[-1].new_status
            elif was_applied:
                status = "Applied"

            historical_jobs.append(
                SimpleNamespace(
                    applied_date=job.applied_date if was_applied else None,
                    status=status,
                    stage=job.stage if status == "Rejected" else None,
                    not_fit_category=(
                        job.not_fit_category if status == "Not a Fit" else None
                    ),
                )
            )

        data = build_sankey_data(historical_jobs)
        application_count = sum(1 for job in historical_jobs if job.applied_date)
        db.session.add(
            SankeySnapshot(
                data_json=json.dumps(data, separators=(",", ":"), sort_keys=True),
                reason=(
                    f"Estimated replay — {current_date.strftime('%b %d, %Y')} "
                    f"({application_count} applications)"
                ),
                created_at=end_of_day,
            )
        )
        current_date += timedelta(days=1)

    db.session.commit()


def _next_action_order():
    has_action = and_(
        Job.next_action.is_not(None),
        func.trim(Job.next_action) != "",
    )
    return (
        case(
            (
                and_(
                    has_action,
                    Job.next_action_date.is_not(None),
                    Job.next_action_date < date.today(),
                ),
                0,
            ),
            (
                and_(
                    has_action,
                    Job.next_action_date == date.today(),
                ),
                1,
            ),
            (
                and_(
                    has_action,
                    Job.next_action_date > date.today(),
                ),
                2,
            ),
            (has_action, 3),
            else_=4,
        ),
        Job.next_action_date.is_(None),
        Job.next_action_date,
    )


def list_jobs(
    search="",
    status="",
    tier="",
    archive="active",
    workflow="",
    sort="default",
):
    query = Job.query
    if archive == "archived":
        query = query.filter(Job.archived.is_(True))
    elif archive != "all":
        query = query.filter(Job.archived.is_(False))
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(Job.company.ilike(like), Job.role.ilike(like), Job.fit_summary.ilike(like))
        )
    if status:
        query = query.filter(Job.status == status.strip())
    if tier:
        query = query.filter(Job.recommendation_tier == tier.strip())
    if workflow == "new":
        query = query.filter(
            Job.applied_date.is_(None),
            Job.status.notin_(
                APPLIED_STATUSES | NON_APPLICATION_TERMINAL_STATUSES
            ),
        )
    elif workflow == "applications":
        query = query.filter(
            or_(
                Job.applied_date.is_not(None),
                Job.status.in_(APPLIED_STATUSES),
            )
        )
    elif workflow == "pursuits":
        candidates = (
            query.filter(
                Job.status.notin_(
                    {
                        "Offer",
                        *TERMINAL_APPLICATION_STATUSES,
                        *NON_APPLICATION_TERMINAL_STATUSES,
                    }
                )
            )
            .order_by(
                *_next_action_order(),
                Job.updated_at.desc(),
            )
            .all()
        )
        return [job for job in candidates if _is_current_pursuit(job)]

    if sort == "freshest":
        return query.order_by(
            Job.first_published_date.is_(None),
            Job.first_published_date.desc(),
            Job.updated_at.desc(),
        ).all()
    if sort == "oldest":
        return query.order_by(
            Job.first_published_date.is_(None),
            Job.first_published_date,
            Job.updated_at.desc(),
        ).all()
    if workflow == "new":
        return query.order_by(
            Job.first_published_date.is_(None),
            Job.first_published_date.desc(),
            Job.updated_at.desc(),
        ).all()
    if workflow == "applications":
        return query.order_by(
            *_next_action_order(),
            Job.applied_date.desc(),
            Job.updated_at.desc(),
        ).all()

    tier_order = case(
        (Job.recommendation_tier == "Apply Next", 1),
        (Job.recommendation_tier == "Prepare Soon", 2),
        (Job.recommendation_tier == "Active Application", 3),
        (Job.recommendation_tier == "Conditional", 4),
        else_=5,
    )
    return query.order_by(
        tier_order,
        Job.recommendation_rank.is_(None),
        Job.recommendation_rank,
        Job.first_published_date.desc(),
        Job.updated_at.desc(),
    ).all()


def _has_confirmed_recruiter_activity(job):
    current_history_notes = [
        item.note
        for item in job.histories
        if item.new_status == job.status and item.note
    ]
    current_evidence = "\n".join(
        value
        for value in (
            job.stage,
            *current_history_notes[:3],
        )
        if value
    )
    if any(
        pattern.search(current_evidence)
        for pattern in (*RECRUITER_ACTIVITY_PATTERNS, *RECRUITER_EVENT_PATTERNS)
    ):
        return True
    return bool(
        job.next_action
        and any(pattern.search(job.next_action) for pattern in RECRUITER_EVENT_PATTERNS)
    )


def _is_current_pursuit(job):
    return job.status in CURRENT_PURSUIT_STATUSES or (
        job.status == "Applied" and _has_confirmed_recruiter_activity(job)
    )


def current_pursuits(limit=25):
    """Return active interview processes and confirmed recruiter conversations."""
    bounded_limit = min(max(limit, 1), 50)
    candidates = (
        Job.query.filter(
            Job.archived.is_(False),
            Job.status.notin_(
                {
                    "Offer",
                    *TERMINAL_APPLICATION_STATUSES,
                    *NON_APPLICATION_TERMINAL_STATUSES,
                }
            ),
        )
        .order_by(
            *_next_action_order(),
            Job.updated_at.desc(),
        )
        .all()
    )
    pursuits = [job for job in candidates if _is_current_pursuit(job)]
    return pursuits[:bounded_limit]


def get_job(job_id):
    job = db.session.get(Job, job_id)
    if job is None:
        raise TrackerNotFoundError(f"Job {job_id} was not found")
    return job


def prepared_resume_path(job, applications_root):
    root = Path(applications_root).resolve()
    company_directory = (root / job.company).resolve()
    try:
        company_directory.relative_to(root)
    except ValueError:
        return None
    if not company_directory.is_dir():
        return None

    candidates = []
    for candidate in company_directory.rglob("*.pdf"):
        if not candidate.is_file() or not candidate.name.lower().endswith(
            "_resume.pdf"
        ):
            continue
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        candidates.append(resolved)

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None

    normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.lower())
    role_key = normalize(job.role)
    role_matches = []
    for candidate in candidates:
        relative_parent = candidate.parent.relative_to(company_directory.resolve())
        folder_keys = [
            normalize(part)
            for part in relative_parent.parts
            if normalize(part)
        ]
        if any(key in role_key or role_key in key for key in folder_keys):
            role_matches.append(candidate)
    return role_matches[0] if len(role_matches) == 1 else None


def create_job(payload):
    job = Job(
        company=(payload.get("company") or "").strip(),
        role=(payload.get("role") or "").strip(),
        status=payload.get("status") or "Researching",
        recommendation_tier=payload.get("recommendation_tier") or "Monitor",
    )
    apply_payload(job, payload)
    sync_application_state(job, payload, status_changed=True)
    if job.status in APPLIED_STATUSES and not job.applied_date:
        job.applied_date = date.today()

    db.session.add(job)
    db.session.flush()
    db.session.add(
        StatusHistory(
            job_id=job.id,
            old_status=None,
            new_status=job.status,
            note=job.decision if job.status == "Not a Fit" else "Job added",
        )
    )
    record_sankey_snapshot(f"Added {job.company} — {job.role}")
    db.session.commit()
    return job


def update_job(job_id, payload):
    job = get_job(job_id)
    old_status = job.status
    apply_payload(job, payload)
    sync_application_state(job, payload, status_changed=job.status != old_status)

    if job.status != old_status:
        db.session.add(
            StatusHistory(
                job_id=job.id,
                old_status=old_status,
                new_status=job.status,
                note=(
                    (payload.get("status_note") or "").strip()
                    or (job.decision if job.status == "Not a Fit" else None)
                ),
            )
        )
        if job.status in APPLIED_STATUSES and not job.applied_date:
            job.applied_date = date.today()

    db.session.flush()
    reason = (
        f"{job.company}: {old_status} → {job.status}"
        if job.status != old_status
        else f"Updated {job.company} — {job.role}"
    )
    record_sankey_snapshot(reason)
    db.session.commit()
    return job


def delete_job(job_id):
    job = get_job(job_id)
    reason = f"Deleted {job.company} — {job.role}"
    db.session.delete(job)
    db.session.flush()
    record_sankey_snapshot(reason)
    db.session.commit()


def stats():
    jobs = Job.query.all()
    active_jobs = [job for job in jobs if not job.archived]
    active_interview_statuses = {
        "Recruiter Screen",
        "Hiring Manager",
        "Technical Interview",
        "System Design",
        "Onsite",
    }
    status_counts = {status: 0 for status in STATUSES}
    for job in active_jobs:
        status_counts[job.status] = status_counts.get(job.status, 0) + 1

    bucket_labels = [
        label for _, _, label in FRESHNESS_BUCKETS
    ] + ["61+ days", "Unknown"]
    freshness_conversion = {
        label: {"bucket": label, "applications": 0, "recruiter_screens": 0}
        for label in bucket_labels
    }

    def reached_recruiter_screen(job):
        progressed_statuses = {
            "Recruiter Screen",
            "Hiring Manager",
            "Technical Interview",
            "System Design",
            "Onsite",
            "Offer",
        }
        if job.status in progressed_statuses:
            return True
        if any(item.new_status in progressed_statuses for item in job.histories):
            return True
        stage = (job.stage or "").lower()
        return job.status == "Rejected" and any(
            marker in stage
            for marker in (
                "recruiter",
                "hiring manager",
                "technical",
                "coding",
                "system design",
                "onsite",
            )
        )

    for job in jobs:
        if not job.applied_date:
            continue
        bucket = freshness_bucket(job.age_at_application_days)
        freshness_conversion[bucket]["applications"] += 1
        if reached_recruiter_screen(job):
            freshness_conversion[bucket]["recruiter_screens"] += 1

    freshness_rows = []
    for label in bucket_labels:
        row = freshness_conversion[label]
        applications = row["applications"]
        row["conversion_rate"] = (
            round(row["recruiter_screens"] * 100 / applications, 1)
            if applications
            else None
        )
        freshness_rows.append(row)

    return {
        "total": len(jobs),
        "applied": sum(1 for job in jobs if job.applied_date),
        "active_applications": sum(
            1
            for job in active_jobs
            if job.status in {"Applied", *active_interview_statuses}
        ),
        "interviews": sum(
            1 for job in active_jobs if job.status in active_interview_statuses
        ),
        "offers": status_counts.get("Offer", 0),
        "follow_ups_due": sum(1 for job in jobs if job.follow_up_due),
        "apply_next": status_counts.get("Ready to Apply", 0),
        "status_counts": status_counts,
        "freshness_conversion": freshness_rows,
    }


def recommendations(limit=8):
    return (
        Job.query.filter(
            Job.archived.is_(False),
            Job.status.notin_(RECOMMENDATION_EXCLUDED_STATUSES),
            Job.recommendation_tier.in_(["Apply Next", "Prepare Soon", "Conditional"]),
        )
        .order_by(
            case(
                (Job.recommendation_tier == "Apply Next", 1),
                (Job.recommendation_tier == "Prepare Soon", 2),
                else_=3,
            ),
            Job.recommendation_rank.is_(None),
            Job.recommendation_rank,
            Job.first_published_date.desc(),
        )
        .limit(limit)
        .all()
    )


def history(limit=12):
    bounded_limit = min(max(limit, 1), 50)
    return (
        StatusHistory.query.order_by(StatusHistory.created_at.desc())
        .limit(bounded_limit)
        .all()
    )


def sankey_snapshots(limit=250):
    bounded_limit = min(max(limit, 1), 1000)
    return (
        SankeySnapshot.query.order_by(SankeySnapshot.created_at.desc())
        .limit(bounded_limit)
        .all()
    )


def _named_sankey_links(data):
    node_names = [node["name"] for node in data.get("nodes", [])]
    links = {}
    for link in data.get("links", []):
        source = (
            link["source"]
            if isinstance(link["source"], str)
            else node_names[link["source"]]
        )
        target = (
            link["target"]
            if isinstance(link["target"], str)
            else node_names[link["target"]]
        )
        links[(source, target)] = links.get((source, target), 0) + link["value"]
    return links


def _rename_sankey_nodes(data, renames):
    if not any(node.get("name") in renames for node in data.get("nodes", [])):
        return data
    return {
        "nodes": [
            {**node, "name": renames.get(node["name"], node["name"])}
            for node in data.get("nodes", [])
        ],
        "links": [
            {
                **link,
                "source": (
                    renames.get(link["source"], link["source"])
                    if isinstance(link["source"], str)
                    else link["source"]
                ),
                "target": (
                    renames.get(link["target"], link["target"])
                    if isinstance(link["target"], str)
                    else link["target"]
                ),
            }
            for link in data.get("links", [])
        ],
    }


def _canonicalize_legacy_sankey(data, technical_active=0):
    data = _rename_sankey_nodes(
        data,
        {"Researching / preparing": "Preparing"},
    )
    links = _named_sankey_links(data)
    if not any(
        source == "Advanced to interviews" or target == "Advanced to interviews"
        for source, target in links
    ):
        return data

    legacy_nodes = {
        "Advanced to interviews",
        "Active interviewing",
        "Final interview",
    }
    canonical_links = {
        (source, target): value
        for (source, target), value in links.items()
        if source not in legacy_nodes and target not in legacy_nodes
    }

    def add(source, target, value):
        if value:
            canonical_links[(source, target)] = (
                canonical_links.get((source, target), 0) + value
            )

    advanced = links.get(("Resume review", "Advanced to interviews"), 0)
    active = links.get(("Advanced to interviews", "Active interviewing"), 0)
    rejected = links.get(
        ("Advanced to interviews", "Rejected during interviews"),
        0,
    )
    final = links.get(("Advanced to interviews", "Final interview"), 0)
    technical_active = min(max(technical_active, 0), active)
    initial_active = active - technical_active

    add("Resume review", "Initial screen", advanced)
    add("Initial screen", "Active initial screen", initial_active)
    add(
        "Initial screen",
        "Technical interview",
        technical_active + rejected + final,
    )
    add(
        "Technical interview",
        "Active technical interview",
        technical_active,
    )
    add("Technical interview", "Rejected during interviews", rejected)
    add("Technical interview", "Final / onsite", final)
    for (source, target), value in links.items():
        if source == "Final interview":
            add("Final / onsite", target, value)

    node_names = []
    for source, target in canonical_links:
        if source not in node_names:
            node_names.append(source)
        if target not in node_names:
            node_names.append(target)
    return {
        "nodes": [{"name": name} for name in node_names],
        "links": [
            {
                "source": node_names.index(source),
                "target": node_names.index(target),
                "value": value,
            }
            for (source, target), value in canonical_links.items()
        ],
    }


def _technical_interview_counts(snapshots):
    if not snapshots:
        return []
    histories = (
        StatusHistory.query.filter(
            StatusHistory.created_at <= snapshots[-1].created_at
        )
        .order_by(StatusHistory.created_at, StatusHistory.id)
        .all()
    )
    current_statuses = {}
    counts = []
    history_index = 0
    technical_statuses = {"Technical Interview", "System Design"}
    for snapshot in snapshots:
        while (
            history_index < len(histories)
            and histories[history_index].created_at <= snapshot.created_at
        ):
            history = histories[history_index]
            current_statuses[history.job_id] = history.new_status
            history_index += 1
        counts.append(
            sum(
                status in technical_statuses
                for status in current_statuses.values()
            )
        )
    return counts


def _sankey_timeline_signature(data):
    topology = []
    links = _named_sankey_links(data)
    incoming = {node["name"]: 0 for node in data.get("nodes", [])}
    for (source, target), value in links.items():
        topology.append((source, target))
        incoming[target] = incoming.get(target, 0) + value

    low_signal_nodes = {
        "Tracked roles",
        "Not applied",
        "Preparing",
        "Researching / preparing",
    }
    milestones = tuple(
        sorted(
            (name, value)
            for name, value in incoming.items()
            if name not in low_signal_nodes
        )
    )
    return tuple(sorted(topology)), milestones


def sankey_timeline(limit=1000):
    snapshots = list(reversed(sankey_snapshots(limit)))
    if not snapshots:
        return {"daily": [], "highlights": [], "all_activity": []}

    entries = []
    signatures = []
    technical_counts = _technical_interview_counts(snapshots)
    for snapshot, technical_count in zip(snapshots, technical_counts):
        entry = snapshot.to_dict()
        entry["grouped_count"] = 1
        entries.append(entry)
        display_data = _canonicalize_legacy_sankey(
            snapshot.data,
            technical_count,
        )
        signatures.append(_sankey_timeline_signature(display_data))

    first_snapshot_is_empty = not snapshots[0].data.get("links")
    if first_snapshot_is_empty:
        entries[0]["empty_state"] = True

    selected = {0, len(snapshots) - 1}
    for index, snapshot in enumerate(snapshots):
        if snapshot.reason.startswith("Estimated replay"):
            selected.add(index)
        if index and signatures[index] != signatures[index - 1]:
            selected.add(index)

    last_index_by_day = {}
    for index, snapshot in enumerate(snapshots):
        last_index_by_day[snapshot.created_at.date()] = index
    selected.update(last_index_by_day.values())

    highlights = []
    previous_index = -1
    for index in sorted(selected):
        entry = dict(entries[index])
        entry["grouped_count"] = index - previous_index
        highlights.append(entry)
        previous_index = index

    if not first_snapshot_is_empty:
        empty_baseline = {
            "id": "empty-baseline",
            "reason": "Timeline start — empty tracker",
            "created_at": datetime.combine(
                snapshots[0].created_at.date(), time.min
            ).isoformat(),
            "grouped_count": 0,
            "empty_state": True,
            "synthetic": True,
            "data": {"nodes": [], "links": []},
        }
        entries.insert(0, empty_baseline)
        highlights.insert(0, dict(empty_baseline))

    daily_indexes = {0}
    last_index_by_day = {}
    for index, entry in enumerate(entries):
        last_index_by_day[datetime.fromisoformat(entry["created_at"]).date()] = index
    daily_indexes.update(last_index_by_day.values())

    daily = []
    previous_index = -1
    for index in sorted(daily_indexes):
        entry = dict(entries[index])
        entry["grouped_count"] = sum(
            candidate["grouped_count"]
            for candidate in entries[previous_index + 1 : index + 1]
        )
        daily.append(entry)
        previous_index = index

    return {
        "daily": daily,
        "highlights": highlights,
        "all_activity": entries,
    }


def get_sankey_snapshot(snapshot_id):
    snapshot = db.session.get(SankeySnapshot, snapshot_id)
    if snapshot is None:
        raise TrackerNotFoundError(f"Sankey snapshot {snapshot_id} was not found")
    return snapshot


def get_sankey_snapshot_view(snapshot_id):
    snapshot = get_sankey_snapshot(snapshot_id)
    technical_count = _technical_interview_counts([snapshot])[0]
    result = snapshot.to_dict()
    result.update(
        _canonicalize_legacy_sankey(snapshot.data, technical_count)
    )
    return result

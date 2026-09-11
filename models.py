import json
from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

FRESHNESS_BUCKETS = (
    (0, 3, "0-3 days"),
    (4, 7, "4-7 days"),
    (8, 14, "8-14 days"),
    (15, 30, "15-30 days"),
    (31, 60, "31-60 days"),
)


def freshness_bucket(days):
    if days is None:
        return "Unknown"
    for minimum, maximum, label in FRESHNESS_BUCKETS:
        if minimum <= days <= maximum:
            return label
    return "61+ days"


def freshness_score(days):
    return {
        "0-3 days": 100,
        "4-7 days": 85,
        "8-14 days": 70,
        "15-30 days": 50,
        "31-60 days": 30,
        "61+ days": 15,
        "Unknown": 0,
    }[freshness_bucket(days)]


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(240), nullable=False)
    status = db.Column(db.String(60), nullable=False, default="Researching")
    stage = db.Column(db.String(100))
    url = db.Column(db.String(700))
    location = db.Column(db.String(240))
    compensation = db.Column(db.String(240))
    fit_summary = db.Column(db.Text)
    decision = db.Column(db.String(120))
    not_fit_category = db.Column(db.String(80))
    recommendation_tier = db.Column(db.String(60), default="Monitor")
    recommendation_rank = db.Column(db.Integer)
    on_call = db.Column(db.String(240))
    risk = db.Column(db.Text)
    next_action = db.Column(db.Text)
    next_action_date = db.Column(db.Date)
    applied_date = db.Column(db.Date)
    first_published_date = db.Column(db.Date)
    posting_updated_date = db.Column(db.Date)
    linkedin_reposted_date = db.Column(db.Date)
    last_verified_date = db.Column(db.Date)
    freshness_source = db.Column(db.String(120))
    freshness_confidence = db.Column(db.String(20))
    notes = db.Column(db.Text)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    histories = db.relationship(
        "StatusHistory",
        backref="job",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="StatusHistory.created_at.desc()",
    )

    @property
    def follow_up_due(self):
        return bool(
            not self.archived
            and self.next_action_date
            and self.next_action_date <= date.today()
            and self.status not in {"Not a Fit", "Rejected", "Withdrawn", "Offer"}
        )

    @property
    def posting_age_days(self):
        if not self.first_published_date:
            return None
        return max((date.today() - self.first_published_date).days, 0)

    @property
    def age_at_application_days(self):
        if not self.first_published_date or not self.applied_date:
            return None
        return max((self.applied_date - self.first_published_date).days, 0)

    def to_dict(self):
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "status": self.status,
            "stage": self.stage,
            "url": self.url,
            "location": self.location,
            "compensation": self.compensation,
            "fit_summary": self.fit_summary,
            "decision": self.decision,
            "not_fit_category": self.not_fit_category,
            "recommendation_tier": self.recommendation_tier,
            "recommendation_rank": self.recommendation_rank,
            "on_call": self.on_call,
            "risk": self.risk,
            "next_action": self.next_action,
            "next_action_date": (
                self.next_action_date.isoformat() if self.next_action_date else None
            ),
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "first_published_date": (
                self.first_published_date.isoformat()
                if self.first_published_date
                else None
            ),
            "posting_updated_date": (
                self.posting_updated_date.isoformat()
                if self.posting_updated_date
                else None
            ),
            "linkedin_reposted_date": (
                self.linkedin_reposted_date.isoformat()
                if self.linkedin_reposted_date
                else None
            ),
            "last_verified_date": (
                self.last_verified_date.isoformat() if self.last_verified_date else None
            ),
            "freshness_source": self.freshness_source,
            "freshness_confidence": self.freshness_confidence,
            "posting_age_days": self.posting_age_days,
            "age_at_application_days": self.age_at_application_days,
            "freshness_bucket": freshness_bucket(self.posting_age_days),
            "freshness_score": freshness_score(self.posting_age_days),
            "notes": self.notes,
            "archived": self.archived,
            "follow_up_due": self.follow_up_due,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StatusHistory(db.Model):
    __tablename__ = "status_history"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    old_status = db.Column(db.String(60))
    new_status = db.Column(db.String(60), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "company": self.job.company,
            "role": self.job.role,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }


class SankeySnapshot(db.Model):
    __tablename__ = "sankey_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    data_json = db.Column(db.Text, nullable=False)
    reason = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    @property
    def data(self):
        return json.loads(self.data_json)

    def to_dict(self, include_data=False):
        result = {
            "id": self.id,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }
        if include_data:
            result.update(self.data)
        return result

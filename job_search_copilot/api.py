from flask import Blueprint, current_app, jsonify, request, send_file, url_for

from .services import (
    TrackerNotFoundError,
    TrackerValidationError,
    backfill_sankey_history,
    build_sankey_data,
    create_job,
    current_pursuits,
    delete_job,
    ensure_sankey_baseline,
    get_job,
    get_sankey_snapshot,
    get_sankey_snapshot_view,
    history,
    list_jobs,
    metadata,
    prepared_resume_path,
    recommendations,
    sankey_timeline,
    sankey_snapshots,
    stats,
    tracker_revision,
    update_job,
)
from .workspace import workspace_status


api_bp = Blueprint("api", __name__, url_prefix="/api")


def job_payload(job):
    payload = job.to_dict()
    resume = prepared_resume_path(job, current_app.config["APPLICATIONS_ROOT"])
    payload["resume_url"] = (
        url_for("api.job_resume_route", job_id=job.id) if resume else None
    )
    return payload


@api_bp.errorhandler(TrackerValidationError)
def validation_error(exc):
    return jsonify({"error": str(exc)}), 400


@api_bp.errorhandler(TrackerNotFoundError)
def not_found_error(exc):
    return jsonify({"error": str(exc)}), 404


@api_bp.get("/meta")
def meta_route():
    return jsonify(metadata())


@api_bp.get("/health")
def health_route():
    return jsonify({"status": "ok"})


@api_bp.get("/revision")
def revision_route():
    return jsonify(tracker_revision())


@api_bp.get("/workspace")
def workspace_route():
    return jsonify(workspace_status(current_app))


@api_bp.get("/jobs")
def list_jobs_route():
    jobs = list_jobs(
        search=request.args.get("q", "").strip(),
        status=request.args.get("status", "").strip(),
        tier=request.args.get("tier", "").strip(),
        archive=request.args.get("archive", "active").strip(),
        workflow=request.args.get("workflow", "").strip(),
        sort=request.args.get("sort", "default").strip(),
    )
    return jsonify([job_payload(job) for job in jobs])


@api_bp.post("/jobs")
def create_job_route():
    job = create_job(request.get_json(silent=True) or {})
    return jsonify(job_payload(job)), 201


@api_bp.put("/jobs/<int:job_id>")
def update_job_route(job_id):
    job = update_job(job_id, request.get_json(silent=True) or {})
    return jsonify(job_payload(job))


@api_bp.delete("/jobs/<int:job_id>")
def delete_job_route(job_id):
    delete_job(job_id)
    return "", 204


@api_bp.get("/jobs/<int:job_id>/resume")
def job_resume_route(job_id):
    job = get_job(job_id)
    resume = prepared_resume_path(job, current_app.config["APPLICATIONS_ROOT"])
    if resume is None:
        raise TrackerNotFoundError(
            f"No unambiguous prepared resume was found for job {job_id}"
        )
    return send_file(
        resume,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=resume.name,
        conditional=True,
    )


@api_bp.get("/stats")
def stats_route():
    return jsonify(stats())


@api_bp.get("/recommendations")
def recommendations_route():
    return jsonify([job_payload(job) for job in recommendations()])


@api_bp.get("/current-pursuits")
def current_pursuits_route():
    return jsonify([job_payload(job) for job in current_pursuits()])


@api_bp.get("/history")
def history_route():
    return jsonify(
        [
            item.to_dict()
            for item in history(request.args.get("limit", 12, type=int))
        ]
    )


@api_bp.get("/sankey")
def sankey_route():
    return jsonify(build_sankey_data())


@api_bp.get("/sankey/snapshots")
def sankey_snapshots_route():
    return jsonify(
        [
            snapshot.to_dict()
            for snapshot in sankey_snapshots(
                request.args.get("limit", 250, type=int)
            )
        ]
    )


@api_bp.get("/sankey/snapshots/<int:snapshot_id>")
def sankey_snapshot_route(snapshot_id):
    return jsonify(get_sankey_snapshot(snapshot_id).to_dict(include_data=True))


@api_bp.get("/sankey/snapshots/<int:snapshot_id>/view")
def sankey_snapshot_view_route(snapshot_id):
    return jsonify(get_sankey_snapshot_view(snapshot_id))


@api_bp.get("/sankey/timeline")
def sankey_timeline_route():
    return jsonify(sankey_timeline(request.args.get("limit", 1000, type=int)))

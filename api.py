from flask import Blueprint, current_app, jsonify, request

from services import (
    TrackerNotFoundError,
    TrackerValidationError,
    backfill_sankey_history,
    build_sankey_data,
    create_job,
    delete_job,
    ensure_sankey_baseline,
    get_sankey_snapshot,
    history,
    list_jobs,
    metadata,
    recommendations,
    sankey_snapshots,
    stats,
    update_job,
)
from workspace import workspace_status


api_bp = Blueprint("api", __name__, url_prefix="/api")


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
    )
    return jsonify([job.to_dict() for job in jobs])


@api_bp.post("/jobs")
def create_job_route():
    job = create_job(request.get_json(silent=True) or {})
    return jsonify(job.to_dict()), 201


@api_bp.put("/jobs/<int:job_id>")
def update_job_route(job_id):
    job = update_job(job_id, request.get_json(silent=True) or {})
    return jsonify(job.to_dict())


@api_bp.delete("/jobs/<int:job_id>")
def delete_job_route(job_id):
    delete_job(job_id)
    return "", 204


@api_bp.get("/stats")
def stats_route():
    return jsonify(stats())


@api_bp.get("/recommendations")
def recommendations_route():
    return jsonify([job.to_dict() for job in recommendations()])


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

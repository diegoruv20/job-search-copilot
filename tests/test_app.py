import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

from app import create_app
from job_search_copilot.models import Job, SankeySnapshot, StatusHistory, db


class ApplicationTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database.close()
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database.name}",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        import os

        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        os.unlink(self.database.name)

    def test_dashboard_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Application dashboard", response.data)
        self.assertIn(b'id="sankey-timeline-range"', response.data)
        self.assertIn(b'id="sankey-timeline-mode"', response.data)
        self.assertIn(b'<option value="highlights">Highlights</option>', response.data)
        self.assertIn(b'<option value="all_activity">All activity</option>', response.data)
        self.assertIn(b'id="sankey-play"', response.data)
        self.assertIn(b'id="sankey-rewind"', response.data)
        self.assertIn(b'class="legend-dot offer"', response.data)
        self.assertIn(b'id="workspace-panel"', response.data)
        self.assertNotIn(b'id="pipeline"', response.data)
        self.assertLess(
            response.data.index(b'id="recommendations"'),
            response.data.index(b'id="sankey-chart"'),
        )
        self.assertLess(
            response.data.index(b'id="sankey-chart"'),
            response.data.index(b'id="freshness-conversion"'),
        )

        script = self.client.get("/static/js/dashboard.js")
        try:
            self.assertEqual(script.status_code, 200)
            self.assertIn(b"sankeyGraph", script.data)
            self.assertIn(b"sankey-flow-motion", script.data)
            self.assertIn(b"updates grouped", script.data)
            self.assertIn(b"sankeyPlaybackDelay", script.data)
            self.assertIn(b"data: snapshot.data || null", script.data)
            self.assertIn(b"Timeline starts empty", script.data)
            self.assertIn(b"compactFrameSubject", script.data)
            self.assertIn(b"Daily snapshot", script.data)
            self.assertIn(b'if (name === "Offer") return "#f5b84b"', script.data)
            self.assertNotIn(b"renderPipeline", script.data)
        finally:
            script.close()

        stylesheet = self.client.get("/static/css/style.css")
        try:
            self.assertEqual(stylesheet.status_code, 200)
            self.assertIn(b"scrollbar-color: #475569 var(--bg)", stylesheet.data)
            self.assertIn(b"*::-webkit-scrollbar-track", stylesheet.data)
        finally:
            stylesheet.close()

    def test_sankey_timeline_keeps_sparse_daily_and_meaningful_changes(self):
        graphs = [
            {
                "nodes": [
                    {"name": "Tracked roles"},
                    {"name": "Researching / preparing"},
                    {"name": "Applied"},
                    {"name": "Resume review"},
                    {"name": "Interviewing"},
                ],
                "links": [
                    {"source": "Tracked roles", "target": "Researching / preparing", "value": 3},
                    {"source": "Applied", "target": "Resume review", "value": 1},
                ],
            },
            {
                "nodes": [
                    {"name": "Tracked roles"},
                    {"name": "Researching / preparing"},
                    {"name": "Applied"},
                    {"name": "Resume review"},
                    {"name": "Interviewing"},
                ],
                "links": [
                    {"source": "Tracked roles", "target": "Researching / preparing", "value": 4},
                    {"source": "Applied", "target": "Resume review", "value": 1},
                ],
            },
            {
                "nodes": [
                    {"name": "Tracked roles"},
                    {"name": "Researching / preparing"},
                    {"name": "Applied"},
                    {"name": "Resume review"},
                    {"name": "Interviewing"},
                ],
                "links": [
                    {"source": "Tracked roles", "target": "Researching / preparing", "value": 4},
                    {"source": "Applied", "target": "Resume review", "value": 1},
                    {"source": "Resume review", "target": "Interviewing", "value": 1},
                ],
            },
            {
                "nodes": [
                    {"name": "Tracked roles"},
                    {"name": "Researching / preparing"},
                    {"name": "Applied"},
                    {"name": "Resume review"},
                    {"name": "Interviewing"},
                ],
                "links": [
                    {"source": "Tracked roles", "target": "Researching / preparing", "value": 5},
                    {"source": "Applied", "target": "Resume review", "value": 1},
                    {"source": "Resume review", "target": "Interviewing", "value": 1},
                ],
            },
        ]
        with self.app.app_context():
            SankeySnapshot.query.delete()
            for index, graph in enumerate(graphs):
                snapshot = SankeySnapshot(
                    reason=f"timeline-{index}",
                    data_json=json.dumps(graph),
                )
                db.session.add(snapshot)
                db.session.flush()
                if index < 2:
                    snapshot.created_at = datetime(2026, 9, 10 + index, 12, 0, 0)
                else:
                    snapshot.created_at = datetime(2026, 9, 11, 13 + index, 0, 0)
            db.session.commit()

        response = self.client.get("/api/sankey/timeline")
        try:
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(len(payload["all_activity"]), 5)
            self.assertEqual(len(payload["highlights"]), 4)
            self.assertEqual(
                [frame["reason"] for frame in payload["highlights"]],
                [
                    "Timeline start — empty tracker",
                    "timeline-0",
                    "timeline-2",
                    "timeline-3",
                ],
            )
            self.assertEqual(
                [frame["grouped_count"] for frame in payload["highlights"]],
                [0, 1, 2, 1],
            )
            self.assertTrue(payload["highlights"][0]["empty_state"])
            self.assertTrue(payload["highlights"][0]["synthetic"])
            self.assertEqual(payload["highlights"][0]["data"], {"nodes": [], "links": []})
            self.assertTrue(
                payload["highlights"][0]["created_at"].startswith("2026-09-10T00:00:00")
            )
        finally:
            response.close()

    def test_workspace_readiness_is_available_to_dashboard(self):
        workspace = {
            "ok": False,
            "checks": {"profile_ready": False},
            "profile": {"ready": False},
        }
        with mock.patch(
            "job_search_copilot.api.workspace_status", return_value=workspace
        ):
            response = self.client.get("/api/workspace")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("checks", payload)
        self.assertIn("profile", payload)
        self.assertFalse(payload["profile"]["ready"])

    def test_job_crud_and_status_history(self):
        create = self.client.post(
            "/api/jobs",
            json={
                "company": "Example",
                "role": "Senior Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
                "recommendation_rank": 1,
            },
        )
        self.assertEqual(create.status_code, 201)
        job = create.get_json()

        update = self.client.put(
            f"/api/jobs/{job['id']}",
            json={"status": "Applied", "status_note": "Submitted"},
        )
        self.assertEqual(update.status_code, 200)
        updated_job = update.get_json()
        self.assertEqual(updated_job["applied_date"], date.today().isoformat())
        self.assertEqual(updated_job["stage"], "Application submitted")
        self.assertEqual(updated_job["recommendation_tier"], "Active Application")
        self.assertIsNone(updated_job["recommendation_rank"])

        history = self.client.get("/api/history").get_json()
        self.assertEqual(history[0]["new_status"], "Applied")
        self.assertEqual(history[0]["note"], "Submitted")

        delete = self.client.delete(f"/api/jobs/{job['id']}")
        self.assertEqual(delete.status_code, 204)
        self.assertEqual(self.client.get("/api/jobs").get_json(), [])

    def test_post_application_status_assigns_applied_date(self):
        create = self.client.post(
            "/api/jobs",
            json={
                "company": "Example",
                "role": "Senior Engineer",
                "status": "Rejected",
                "stage": "Technical Interview",
                "recommendation_tier": "Monitor",
            },
        )
        self.assertEqual(create.status_code, 201)
        job = create.get_json()
        self.assertEqual(job["applied_date"], date.today().isoformat())

        sankey = self.client.get("/api/sankey").get_json()
        node_indexes = {
            node["name"]: index for index, node in enumerate(sankey["nodes"])
        }
        interview_rejection = next(
            link
            for link in sankey["links"]
            if link["source"] == node_indexes["Advanced to interviews"]
            and link["target"] == node_indexes["Rejected during interviews"]
        )
        self.assertEqual(interview_rejection["value"], 1)

    def test_stats_and_recommendations(self):
        with self.app.app_context():
            db.session.add_all(
                [
                    Job(
                        company="Applied Co",
                        role="Engineer",
                        status="Applied",
                        applied_date=date.today(),
                        recommendation_tier="Active Application",
                    ),
                    Job(
                        company="Next Co",
                        role="Platform Engineer",
                        status="Ready to Apply",
                        recommendation_tier="Apply Next",
                        recommendation_rank=1,
                    ),
                    Job(
                        company="Archived Co",
                        role="Old opportunity",
                        status="Ready to Apply",
                        recommendation_tier="Apply Next",
                        archived=True,
                    ),
                ]
            )
            db.session.commit()

        stats = self.client.get("/api/stats").get_json()
        self.assertEqual(stats["applied"], 1)
        self.assertEqual(stats["active_applications"], 1)
        self.assertEqual(stats["apply_next"], 1)

        recommendations = self.client.get("/api/recommendations").get_json()
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["company"], "Next Co")

    def test_active_application_is_not_recommended(self):
        with self.app.app_context():
            db.session.add(
                Job(
                    company="Stale Co",
                    role="Submitted opportunity",
                    status="Applied",
                    applied_date=date.today(),
                    recommendation_tier="Apply Next",
                    recommendation_rank=1,
                )
            )
            db.session.commit()

        self.assertEqual(self.client.get("/api/recommendations").get_json(), [])

    def test_not_a_fit_is_terminal_without_becoming_an_application(self):
        create = self.client.post(
            "/api/jobs",
            json={
                "company": "Mismatch Co",
                "role": "Infrastructure Engineer",
                "status": "Researching",
                "recommendation_tier": "Conditional",
                "recommendation_rank": 1,
                "next_action_date": date.today().isoformat(),
            },
        )
        self.assertEqual(create.status_code, 201)
        job = create.get_json()

        update = self.client.put(
            f"/api/jobs/{job['id']}",
            json={
                "status": "Not a Fit",
                "not_fit_category": "Required technology stack",
                "decision": "Do not apply",
                "status_note": "Required experience is outside the target profile",
            },
        )
        self.assertEqual(update.status_code, 200)
        updated_job = update.get_json()
        self.assertIsNone(updated_job["applied_date"])
        self.assertEqual(updated_job["stage"], "Not selected for application")
        self.assertEqual(updated_job["recommendation_tier"], "Monitor")
        self.assertIsNone(updated_job["recommendation_rank"])
        self.assertIsNone(updated_job["next_action_date"])
        self.assertFalse(updated_job["follow_up_due"])
        self.assertEqual(self.client.get("/api/recommendations").get_json(), [])

        sankey = self.client.get("/api/sankey").get_json()
        node_indexes = {
            node["name"]: index for index, node in enumerate(sankey["nodes"])
        }
        not_fit_link = next(
            link
            for link in sankey["links"]
            if link["source"] == node_indexes["Not applied"]
            and link["target"] == node_indexes["Not a fit"]
        )
        self.assertEqual(not_fit_link["value"], 1)
        category_link = next(
            link
            for link in sankey["links"]
            if link["source"] == node_indexes["Not a fit"]
            and link["target"] == node_indexes["Required technology stack"]
        )
        self.assertEqual(category_link["value"], 1)

    def test_not_a_fit_requires_an_auditable_decision_reason(self):
        create = self.client.post(
            "/api/jobs",
            json={
                "company": "Unclear Co",
                "role": "Platform Engineer",
                "status": "Researching",
            },
        )
        job = create.get_json()

        update = self.client.put(
            f"/api/jobs/{job['id']}",
            json={
                "status": "Not a Fit",
                "not_fit_category": "Required technology stack",
            },
        )
        self.assertEqual(update.status_code, 400)
        self.assertEqual(
            update.get_json()["error"],
            "A decision reason is required for Not a Fit jobs",
        )

    def test_not_a_fit_requires_a_primary_category(self):
        create = self.client.post(
            "/api/jobs",
            json={
                "company": "Uncategorized Co",
                "role": "Platform Engineer",
                "status": "Researching",
            },
        )
        job = create.get_json()

        update = self.client.put(
            f"/api/jobs/{job['id']}",
            json={
                "status": "Not a Fit",
                "decision": "The required stack is not a match",
            },
        )
        self.assertEqual(update.status_code, 400)
        self.assertEqual(
            update.get_json()["error"],
            "A primary Not a Fit category is required",
        )

    def test_archived_jobs_are_hidden_by_default(self):
        with self.app.app_context():
            db.session.add_all(
                [
                    Job(
                        company="Active Co",
                        role="Engineer",
                        status="Researching",
                        recommendation_tier="Monitor",
                    ),
                    Job(
                        company="Archived Co",
                        role="Engineer",
                        status="Hold",
                        recommendation_tier="Apply Next",
                        archived=True,
                    ),
                    Job(
                        company="Archived Rejection Co",
                        role="Engineer",
                        status="Rejected",
                        stage="Resume Screen Rejection",
                        applied_date=date.today(),
                        recommendation_tier="Monitor",
                        archived=True,
                    ),
                ]
            )
            db.session.commit()

        active_jobs = self.client.get("/api/jobs").get_json()
        self.assertEqual([job["company"] for job in active_jobs], ["Active Co"])

        archived_jobs = self.client.get("/api/jobs?archive=archived").get_json()
        self.assertEqual(
            [job["company"] for job in archived_jobs],
            ["Archived Co", "Archived Rejection Co"],
        )
        self.assertEqual(self.client.get("/api/recommendations").get_json(), [])

        sankey = self.client.get("/api/sankey").get_json()
        node_names = [node["name"] for node in sankey["nodes"]]
        self.assertNotIn("On hold", node_names)
        tracked_links = [
            link
            for link in sankey["links"]
            if node_names[link["source"]] == "Tracked roles"
        ]
        self.assertEqual(sum(link["value"] for link in tracked_links), 2)
        self.assertIn("Rejected at resume review", node_names)

    def test_invalid_date_is_rejected(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Example",
                "role": "Engineer",
                "status": "Researching",
                "recommendation_tier": "Monitor",
                "next_action_date": "tomorrow",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ISO date", response.get_json()["error"])

    def test_freshness_fields_and_derived_age(self):
        today = date.today()
        published = today.replace(day=max(1, today.day - 2))
        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Fresh Co",
                "role": "Data Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
                "first_published_date": published.isoformat(),
                "posting_updated_date": today.isoformat(),
                "linkedin_reposted_date": today.isoformat(),
                "last_verified_date": today.isoformat(),
                "freshness_source": "Official ATS",
                "freshness_confidence": "High",
            },
        )
        self.assertEqual(response.status_code, 201)
        job = response.get_json()
        self.assertEqual(job["first_published_date"], published.isoformat())
        self.assertEqual(job["posting_age_days"], (today - published).days)
        self.assertEqual(job["freshness_bucket"], "0-3 days")
        self.assertEqual(job["freshness_score"], 100)

    def test_invalid_freshness_confidence_is_rejected(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Uncertain Co",
                "role": "Engineer",
                "freshness_confidence": "Certain-ish",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"], "Invalid freshness confidence"
        )

    def test_boolean_and_priority_fields_are_strictly_validated(self):
        archived = self.client.post(
            "/api/jobs",
            json={
                "company": "Boolean Co",
                "role": "Engineer",
                "archived": "false",
            },
        )
        self.assertEqual(archived.status_code, 400)
        self.assertEqual(archived.get_json()["error"], "archived must be a boolean")

        rank = self.client.post(
            "/api/jobs",
            json={
                "company": "Rank Co",
                "role": "Engineer",
                "recommendation_rank": 0,
            },
        )
        self.assertEqual(rank.status_code, 400)
        self.assertEqual(
            rank.get_json()["error"],
            "recommendation_rank must be greater than zero",
        )

    def test_stats_report_conversion_by_application_freshness(self):
        today = date.today()
        with self.app.app_context():
            screened = Job(
                company="Screened Co",
                role="Engineer",
                status="Recruiter Screen",
                applied_date=today,
                first_published_date=today,
                recommendation_tier="Active Application",
            )
            rejected = Job(
                company="Rejected Co",
                role="Engineer",
                status="Rejected",
                stage="Resume Screen Rejection",
                applied_date=today,
                first_published_date=today,
                recommendation_tier="Monitor",
            )
            unknown = Job(
                company="Unknown Co",
                role="Engineer",
                status="Applied",
                applied_date=today,
                recommendation_tier="Active Application",
            )
            db.session.add_all([screened, rejected, unknown])
            db.session.commit()

        stats = self.client.get("/api/stats").get_json()
        buckets = {row["bucket"]: row for row in stats["freshness_conversion"]}
        self.assertEqual(buckets["0-3 days"]["applications"], 2)
        self.assertEqual(buckets["0-3 days"]["recruiter_screens"], 1)
        self.assertEqual(buckets["0-3 days"]["conversion_rate"], 50.0)
        self.assertEqual(buckets["Unknown"]["applications"], 1)

    def test_unsafe_url_is_rejected(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Example",
                "role": "Engineer",
                "status": "Researching",
                "recommendation_tier": "Monitor",
                "url": "javascript:alert(1)",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("URL must start", response.get_json()["error"])

    def test_sankey_groups_rejections_by_stage(self):
        with self.app.app_context():
            db.session.add_all(
                [
                    Job(
                        company="Rejected Co",
                        role="Engineer",
                        status="Rejected",
                        stage="Resume Screen Rejection",
                        applied_date=date.today(),
                        recommendation_tier="Monitor",
                    ),
                    Job(
                        company="Active Co",
                        role="Engineer",
                        status="Recruiter Screen",
                        applied_date=date.today(),
                        recommendation_tier="Active Application",
                    ),
                    Job(
                        company="Future Co",
                        role="Engineer",
                        status="Ready to Apply",
                        recommendation_tier="Apply Next",
                    ),
                    Job(
                        company="Final Loop Co",
                        role="Engineer",
                        status="Rejected",
                        stage="Final Interview Rejection",
                        applied_date=date.today(),
                        recommendation_tier="Monitor",
                    ),
                ]
            )
            db.session.commit()

        data = self.client.get("/api/sankey").get_json()
        nodes = {node["name"] for node in data["nodes"]}
        self.assertIn("Resume review", nodes)
        self.assertIn("Rejected at resume review", nodes)
        self.assertIn("Rejected after final interview", nodes)
        self.assertIn("Active interviewing", nodes)
        self.assertIn("Ready to apply", nodes)

    def test_sankey_keeps_withdrawn_beside_resume_review_outcomes(self):
        with self.app.app_context():
            db.session.add(
                Job(
                    company="Withdrawn Co",
                    role="Engineer",
                    status="Withdrawn",
                    stage="Final Interview",
                    applied_date=date.today(),
                    recommendation_tier="Monitor",
                )
            )
            db.session.commit()

        data = self.client.get("/api/sankey").get_json()
        nodes = [node["name"] for node in data["nodes"]]
        links = {
            (nodes[link["source"]], nodes[link["target"]])
            for link in data["links"]
        }
        self.assertIn(("Resume review", "Withdrawn"), links)
        self.assertNotIn(("Final interview", "Withdrawn"), links)

    def test_sankey_snapshot_history_tracks_funnel_changes(self):
        baseline = self.client.get("/api/sankey/snapshots").get_json()
        self.assertEqual(len(baseline), 1)
        self.assertEqual(baseline[0]["reason"], "History tracking started")
        initial_timeline = self.client.get("/api/sankey/timeline").get_json()
        self.assertEqual(len(initial_timeline["highlights"]), 1)
        self.assertTrue(initial_timeline["highlights"][0]["empty_state"])
        self.assertNotIn("synthetic", initial_timeline["highlights"][0])

        created = self.client.post(
            "/api/jobs",
            json={
                "company": "Snapshot Co",
                "role": "Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
            },
        ).get_json()
        after_create = self.client.get("/api/sankey/snapshots").get_json()
        self.assertEqual(len(after_create), 2)

        self.client.put(
            f"/api/jobs/{created['id']}",
            json={"status": "Applied"},
        )
        after_apply = self.client.get("/api/sankey/snapshots").get_json()
        self.assertEqual(len(after_apply), 3)
        self.assertIn("Ready to Apply", after_apply[0]["reason"])
        self.assertIn("Applied", after_apply[0]["reason"])

        historical = self.client.get(
            f"/api/sankey/snapshots/{after_create[0]['id']}"
        ).get_json()
        node_names = [node["name"] for node in historical["nodes"]]
        self.assertIn("Ready to apply", node_names)
        self.assertNotIn("Applied", node_names)

    def test_sankey_timeline_groups_dense_low_signal_activity(self):
        def graph(researching, ready=0):
            nodes = [
                {"name": "Tracked roles"},
                {"name": "Not applied"},
                {"name": "Researching / preparing"},
            ]
            links = [
                {"source": 0, "target": 1, "value": researching + ready},
                {"source": 1, "target": 2, "value": researching},
            ]
            if ready:
                nodes.append({"name": "Ready to apply"})
                links.append({"source": 1, "target": 3, "value": ready})
            return {"nodes": nodes, "links": links}

        with self.app.app_context():
            SankeySnapshot.query.delete()
            snapshots = [
                SankeySnapshot(
                    data_json=json.dumps(graph(1)),
                    reason="Added Alpha — Engineer",
                    created_at=datetime(2026, 9, 11, 9, 0),
                ),
                SankeySnapshot(
                    data_json=json.dumps(graph(2)),
                    reason="Added Bravo — Engineer",
                    created_at=datetime(2026, 9, 11, 9, 5),
                ),
                SankeySnapshot(
                    data_json=json.dumps(graph(3)),
                    reason="Added Charlie — Engineer",
                    created_at=datetime(2026, 9, 11, 9, 10),
                ),
                SankeySnapshot(
                    data_json=json.dumps(graph(2, ready=1)),
                    reason="Charlie: Researching → Ready to Apply",
                    created_at=datetime(2026, 9, 11, 9, 15),
                ),
                SankeySnapshot(
                    data_json=json.dumps(graph(3, ready=1)),
                    reason="Added Delta — Engineer",
                    created_at=datetime(2026, 9, 11, 9, 20),
                ),
                SankeySnapshot(
                    data_json=json.dumps(graph(4, ready=1)),
                    reason="Estimated replay — Sep 12, 2026 (0 applications)",
                    created_at=datetime(2026, 9, 12, 23, 59),
                ),
            ]
            db.session.add_all(snapshots)
            db.session.commit()

        timeline = self.client.get("/api/sankey/timeline").get_json()
        self.assertEqual(len(timeline["all_activity"]), 7)
        self.assertEqual(
            [frame["reason"] for frame in timeline["highlights"]],
            [
                "Timeline start — empty tracker",
                "Added Alpha — Engineer",
                "Charlie: Researching → Ready to Apply",
                "Added Delta — Engineer",
                "Estimated replay — Sep 12, 2026 (0 applications)",
            ],
        )
        self.assertEqual(
            [frame["grouped_count"] for frame in timeline["highlights"]],
            [0, 1, 3, 1, 1],
        )
        self.assertEqual(
            [frame["grouped_count"] for frame in timeline["all_activity"]],
            [0, 1, 1, 1, 1, 1, 1],
        )

    def test_non_funnel_edit_does_not_create_sankey_snapshot(self):
        created = self.client.post(
            "/api/jobs",
            json={
                "company": "Notes Co",
                "role": "Engineer",
                "status": "Researching",
                "recommendation_tier": "Monitor",
            },
        ).get_json()
        before = len(self.client.get("/api/sankey/snapshots").get_json())

        self.client.put(
            f"/api/jobs/{created['id']}",
            json={"notes": "Updated without changing the funnel"},
        )

        after = len(self.client.get("/api/sankey/snapshots").get_json())
        self.assertEqual(after, before)

    def test_historical_sankey_backfill_uses_application_dates(self):
        from job_search_copilot.api import (
            backfill_sankey_history,
            ensure_sankey_baseline,
        )

        yesterday = date.today() - timedelta(days=1)
        with self.app.app_context():
            SankeySnapshot.query.delete()
            job = Job(
                company="Historical Co",
                role="Engineer",
                status="Rejected",
                stage="Resume Screen Rejection",
                applied_date=yesterday,
                recommendation_tier="Monitor",
                created_at=datetime.now(),
            )
            db.session.add(job)
            db.session.flush()
            db.session.add(
                StatusHistory(
                    job_id=job.id,
                    old_status="Applied",
                    new_status="Rejected",
                    created_at=datetime.now(),
                )
            )
            db.session.commit()
            ensure_sankey_baseline()
            backfill_sankey_history()

        snapshots = self.client.get("/api/sankey/snapshots").get_json()
        estimated = next(
            snapshot
            for snapshot in snapshots
            if snapshot["reason"].startswith("Estimated replay")
        )
        historical = self.client.get(
            f"/api/sankey/snapshots/{estimated['id']}"
        ).get_json()
        node_names = [node["name"] for node in historical["nodes"]]
        self.assertIn("Applied", node_names)
        self.assertNotIn("Rejected", node_names)


if __name__ == "__main__":
    unittest.main()

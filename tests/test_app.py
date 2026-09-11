import tempfile
import unittest
from datetime import date, datetime, timedelta

from app import create_app
from models import Job, SankeySnapshot, StatusHistory, db


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
        self.assertIn(b'id="sankey-play"', response.data)
        self.assertIn(b'id="sankey-rewind"', response.data)

        script = self.client.get("/static/js/dashboard.js")
        try:
            self.assertEqual(script.status_code, 200)
            self.assertIn(b"sankeyGraph", script.data)
            self.assertIn(b"sankey-flow-motion", script.data)
        finally:
            script.close()

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
        technical_link = next(
            link
            for link in sankey["links"]
            if link["source"] == node_indexes["Rejected"]
            and link["target"] == node_indexes["Rejected after technical stage"]
        )
        self.assertEqual(technical_link["value"], 1)

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
        self.assertIn("Rejected at resume screen", node_names)

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
                ]
            )
            db.session.commit()

        data = self.client.get("/api/sankey").get_json()
        nodes = {node["name"] for node in data["nodes"]}
        self.assertIn("Rejected", nodes)
        self.assertIn("Rejected at resume screen", nodes)
        self.assertIn("Recruiter screen", nodes)
        self.assertIn("Ready to apply", nodes)

    def test_sankey_snapshot_history_tracks_funnel_changes(self):
        baseline = self.client.get("/api/sankey/snapshots").get_json()
        self.assertEqual(len(baseline), 1)
        self.assertEqual(baseline[0]["reason"], "History tracking started")

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
        from api import backfill_sankey_history, ensure_sankey_baseline

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

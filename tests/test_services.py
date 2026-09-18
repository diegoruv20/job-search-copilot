import os
import tempfile
import unittest

from app import create_app
from job_search_copilot.models import StatusHistory, db
from job_search_copilot.services import (
    TrackerValidationError,
    create_job,
    current_pursuits,
    list_jobs,
    stats,
    update_job,
)


class TrackerServiceTestCase(unittest.TestCase):
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
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()
        os.unlink(self.database.name)

    def test_service_mutations_are_visible_through_rest_api(self):
        job = create_job(
            {
                "company": "Example Systems",
                "role": "Data Platform Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
                "recommendation_rank": 1,
            }
        )

        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()[0]["id"], job.id)

        update_job(job.id, {"status": "Applied", "status_note": "Submitted"})
        updated = self.client.get("/api/jobs").get_json()[0]
        self.assertEqual(updated["status"], "Applied")
        self.assertEqual(updated["stage"], "Application submitted")
        self.assertEqual(stats()["applied"], 1)

    def test_rest_mutations_are_visible_through_services(self):
        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Sample Analytics",
                "role": "Backend Engineer",
                "status": "Researching",
                "recommendation_tier": "Conditional",
            },
        )
        self.assertEqual(response.status_code, 201)
        jobs = list_jobs(search="Sample")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "Sample Analytics")

    def test_service_validation_matches_api_validation(self):
        with self.assertRaisesRegex(
            TrackerValidationError, "URL must start with http:// or https://"
        ):
            create_job(
                {
                    "company": "Unsafe Example",
                    "role": "Engineer",
                    "url": "javascript:alert(1)",
                }
            )

        response = self.client.post(
            "/api/jobs",
            json={
                "company": "Unsafe Example",
                "role": "Engineer",
                "url": "javascript:alert(1)",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"], "URL must start with http:// or https://"
        )

    def test_current_pursuits_are_derived_from_shared_domain_evidence(self):
        create_job(
            {
                "company": "Interview Co",
                "role": "Platform Engineer",
                "status": "Technical Interview",
                "stage": "Technical interview scheduled",
            }
        )
        scheduled_call = create_job(
            {
                "company": "Scheduled Co",
                "role": "Data Engineer",
                "status": "Applied",
                "stage": "Recruiter introductory call scheduled for Friday",
            }
        )
        recruiter_response = create_job(
            {
                "company": "Response Co",
                "role": "Backend Engineer",
                "status": "Applied",
            }
        )
        db.session.add(
            StatusHistory(
                job_id=recruiter_response.id,
                old_status="Applied",
                new_status="Applied",
                note="The recruiter replied and invited a call.",
            )
        )
        create_job(
            {
                "company": "Awaiting Co",
                "role": "Engineer",
                "status": "Applied",
                "next_action": "Follow up if there is no response",
            }
        )
        create_job(
            {
                "company": "Rejected Co",
                "role": "Engineer",
                "status": "Rejected",
                "stage": "Recruiter call confirmed",
            }
        )
        db.session.commit()

        pursuits = current_pursuits()
        self.assertEqual(
            {job.company for job in pursuits},
            {"Interview Co", "Scheduled Co", "Response Co"},
        )
        self.assertIn(scheduled_call, pursuits)
        self.assertEqual(
            {job.company for job in list_jobs(workflow="pursuits")},
            {"Interview Co", "Scheduled Co", "Response Co"},
        )
        response = self.client.get("/api/current-pursuits")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {job["company"] for job in response.get_json()},
            {"Interview Co", "Scheduled Co", "Response Co"},
        )

    def test_current_pursuits_blank_state(self):
        self.assertEqual(current_pursuits(), [])
        self.assertEqual(self.client.get("/api/current-pursuits").get_json(), [])

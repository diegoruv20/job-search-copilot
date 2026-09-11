import os
import tempfile
import unittest

from app import create_app
from job_search_copilot.models import db
from job_search_copilot.services import (
    TrackerValidationError,
    create_job,
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

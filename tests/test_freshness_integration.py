import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

from app import create_app
from models import db
from sqlalchemy import text


class FreshnessIntegrationTestCase(unittest.TestCase):
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
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        os.unlink(self.database.name)

    def test_freshness_flows_through_queue_and_conversion_stats(self):
        published = date.today() - timedelta(days=2)
        created = self.client.post(
            "/api/jobs",
            json={
                "company": "Fresh Platform Co",
                "role": "Senior Data Platform Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
                "recommendation_rank": 1,
                "first_published_date": published.isoformat(),
                "last_verified_date": date.today().isoformat(),
                "freshness_source": "Official ATS",
                "freshness_confidence": "High",
            },
        )
        self.assertEqual(created.status_code, 201)
        job = created.get_json()

        recommendations = self.client.get("/api/recommendations").get_json()
        self.assertEqual(recommendations[0]["id"], job["id"])
        self.assertEqual(recommendations[0]["freshness_bucket"], "0-3 days")

        applied = self.client.put(
            f"/api/jobs/{job['id']}",
            json={"status": "Recruiter Screen", "applied_date": date.today().isoformat()},
        )
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.get_json()["age_at_application_days"], 2)

        buckets = {
            row["bucket"]: row
            for row in self.client.get("/api/stats").get_json()[
                "freshness_conversion"
            ]
        }
        self.assertEqual(buckets["0-3 days"]["applications"], 1)
        self.assertEqual(buckets["0-3 days"]["recruiter_screens"], 1)
        self.assertEqual(buckets["0-3 days"]["conversion_rate"], 100.0)

        dashboard = self.client.get("/")
        self.assertIn(b"Freshness and recruiter-screen conversion", dashboard.data)
        self.assertIn(b'input id="first-published-date"', dashboard.data)


class ExistingDatabaseUpgradeTestCase(unittest.TestCase):
    def test_existing_jobs_table_receives_freshness_columns(self):
        database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        database.close()
        connection = sqlite3.connect(database.name)
        connection.execute(
            """
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY,
                company VARCHAR(120) NOT NULL,
                role VARCHAR(240) NOT NULL,
                status VARCHAR(60) NOT NULL,
                recommendation_tier VARCHAR(60),
                archived BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO jobs (
                id, company, role, status, recommendation_tier,
                archived, created_at, updated_at
            ) VALUES (
                1, 'Existing Co', 'Engineer', 'Researching', 'Monitor',
                0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
        connection.close()

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.name}",
            }
        )
        with app.app_context():
            columns = {
                row[1]
                for row in db.session.execute(
                    text("PRAGMA table_info(jobs)")
                ).all()
            }
            self.assertIn("first_published_date", columns)
            self.assertIn("freshness_confidence", columns)
            count = db.session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE company = 'Existing Co'")
            ).scalar_one()
            self.assertEqual(count, 1)
            db.session.remove()
            db.engine.dispose()

        os.unlink(database.name)


if __name__ == "__main__":
    unittest.main()

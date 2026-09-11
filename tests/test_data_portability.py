import json
import os
import tempfile
import unittest
from pathlib import Path

from app import create_app
from data_portability import (
    backup_database,
    export_json,
    import_json,
    load_demo,
    restore_database,
)
from models import Job, SankeySnapshot, StatusHistory, db
from services import create_job


class DataPortabilityTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "tracker.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
            }
        )
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        self.temp_dir.cleanup()

    def test_blank_first_run_and_opt_in_demo(self):
        self.assertEqual(Job.query.count(), 0)
        result = load_demo()
        self.assertEqual(len(result["jobs"]), 3)
        self.assertEqual(Job.query.count(), 3)
        self.assertTrue(all("Fictional" in job.notes for job in Job.query.all()))

        with self.assertRaisesRegex(ValueError, "not empty"):
            load_demo()

    def test_backup_and_restore_preserve_state(self):
        create_job({"company": "Original Co", "role": "Engineer"})
        backup_path = Path(self.temp_dir.name) / "backup.db"
        backup_database(backup_path)

        SankeySnapshot.query.delete()
        StatusHistory.query.delete()
        Job.query.delete()
        db.session.commit()
        self.assertEqual(Job.query.count(), 0)

        with self.assertRaisesRegex(ValueError, "confirm=True"):
            restore_database(backup_path)

        restore_database(backup_path, confirm=True)
        self.assertEqual(Job.query.count(), 1)
        self.assertEqual(Job.query.one().company, "Original Co")

    def test_json_round_trip_and_replace_guard(self):
        create_job(
            {
                "company": "Portable Co",
                "role": "Platform Engineer",
                "status": "Ready to Apply",
                "recommendation_tier": "Apply Next",
            }
        )
        export_path = Path(self.temp_dir.name) / "tracker.json"
        export_json(export_path)
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["jobs"][0]["company"], "Portable Co")

        with self.assertRaisesRegex(ValueError, "not empty"):
            import_json(export_path)

        result = import_json(export_path, replace=True)
        self.assertEqual(result["jobs"], 1)
        self.assertEqual(Job.query.one().role, "Platform Engineer")

    def test_import_rejects_invalid_shape_before_replacing(self):
        create_job({"company": "Keep Me", "role": "Engineer"})
        invalid_path = Path(self.temp_dir.name) / "invalid.json"
        invalid_path.write_text(
            json.dumps({"version": 1, "jobs": [{"company": "Missing Role"}]}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "company and role"):
            import_json(invalid_path, replace=True)
        self.assertEqual(Job.query.one().company, "Keep Me")

    def test_import_validates_job_rules_before_replacing(self):
        create_job({"company": "Keep Me", "role": "Engineer"})
        export_path = Path(self.temp_dir.name) / "invalid-status.json"
        export_json(export_path)
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        payload["jobs"][0]["status"] = "Maybe"
        export_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Invalid status"):
            import_json(export_path, replace=True)
        self.assertEqual(Job.query.one().company, "Keep Me")

    def test_restore_rejects_non_tracker_database(self):
        create_job({"company": "Keep Me", "role": "Engineer"})
        invalid_path = Path(self.temp_dir.name) / "not-a-tracker.db"
        invalid_path.write_text("not sqlite", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "valid SQLite"):
            restore_database(invalid_path, confirm=True)
        self.assertEqual(Job.query.one().company, "Keep Me")

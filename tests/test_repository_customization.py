import re
import json
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class RepositoryCustomizationTestCase(unittest.TestCase):
    def test_required_customization_files_exist(self):
        required = [
            ROOT / ".github" / "copilot-instructions.md",
            ROOT / ".github" / "mcp.json",
            ROOT / ".github" / "skills" / "job-search" / "SKILL.md",
            ROOT / ".github" / "skills" / "resume-making" / "SKILL.md",
            ROOT / ".github" / "skills" / "application-tracking" / "SKILL.md",
            ROOT / ".github" / "skills" / "outreach" / "SKILL.md",
            ROOT / ".github" / "skills" / "interview-prep" / "SKILL.md",
            ROOT / ".github" / "skills" / "profile-onboarding" / "SKILL.md",
            ROOT / ".github" / "agents" / "career-discovery.agent.md",
            ROOT / ".github" / "agents" / "job-search.agent.md",
            ROOT / ".github" / "agents" / "application-strategist.agent.md",
            ROOT / ".github" / "agents" / "interview-coach.agent.md",
            ROOT / "config" / "user_profile.example.md",
            ROOT / "config" / "experience_inventory.example.md",
            ROOT / "scripts" / "bootstrap.py",
            ROOT / "scripts" / "mcp_launcher.py",
            ROOT / "scripts" / "mcp_smoke.py",
            ROOT / "scripts" / "privacy_scan.py",
            ROOT / "scripts" / "release_check.py",
            ROOT / "docs" / "architecture.md",
            ROOT / "docs" / "workflows.md",
            ROOT / "docs" / "data-and-privacy.md",
            ROOT / "docs" / "troubleshooting.md",
            ROOT / "docs" / "profile-onboarding.md",
        ]
        self.assertEqual([str(path) for path in required if not path.is_file()], [])

    def test_skill_frontmatter_has_name_and_description(self):
        for skill_path in (ROOT / ".github" / "skills").glob("*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill_path)
            frontmatter = text.split("---", 2)[1]
            self.assertRegex(frontmatter, r"(?m)^name: [a-z0-9-]+$")
            self.assertRegex(frontmatter, r"(?m)^description: .+$")

    def test_mcp_launcher_uses_checkout_virtual_environment(self):
        from scripts.mcp_launcher import main, virtualenv_python

        with self.subTest("Windows layout"):
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "repo with spaces"
                python = root / ".venv" / "Scripts" / "python.exe"
                python.parent.mkdir(parents=True)
                python.touch()
                self.assertEqual(virtualenv_python(root), python)
                with mock.patch(
                    "scripts.mcp_launcher.subprocess.run",
                    return_value=mock.Mock(returncode=0),
                ) as run:
                    self.assertEqual(main(root), 0)
                run.assert_called_once_with(
                    [str(python), str(root / "mcp_server.py")],
                    cwd=root,
                )

    def test_privacy_scan_passes_for_tracked_files(self):
        from scripts.privacy_scan import scan

        self.assertEqual(scan(), [])

    def test_bootstrap_explains_progress_and_failure(self):
        script = (ROOT / "scripts" / "bootstrap.py").read_text(encoding="utf-8")
        self.assertIn("[{number}/{TOTAL_STEPS}]", script)
        self.assertIn("[OK]", script)
        self.assertIn("[SKIP]", script)
        self.assertIn("[ERROR] Setup stopped before completion.", script)
        self.assertIn("Setup complete", script)

    def test_repository_configures_tracker_and_playwright_mcp(self):
        config = json.loads(
            (ROOT / ".github" / "mcp.json").read_text(encoding="utf-8")
        )
        servers = config["mcpServers"]
        self.assertEqual(
            servers["job-search-copilot"]["args"],
            ["-3", "scripts/mcp_launcher.py"],
        )
        self.assertEqual(servers["playwright"]["command"], "npx")
        self.assertEqual(
            servers["playwright"]["args"],
            ["@playwright/mcp@0.0.80"],
        )

    def test_profile_readiness_requires_completed_interviews(self):
        import tempfile

        from workspace import profile_status

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "local"
            config = root / "config"
            docs = root / "docs"
            local.mkdir()
            config.mkdir()
            docs.mkdir()
            (config / "user_profile.example.md").write_text("", encoding="utf-8")
            (config / "experience_inventory.example.md").write_text(
                "", encoding="utf-8"
            )

            missing = profile_status(root)
            self.assertFalse(missing["ready"])
            self.assertEqual(
                missing["user_profile"]["interview_status"], "missing"
            )

            (local / "user_profile.md").write_text(
                "- Interview status: in progress\n"
                "- [Needs follow-up] Confirm location\n",
                encoding="utf-8",
            )
            (local / "experience_inventory.md").write_text(
                "- Interview status: ready\n", encoding="utf-8"
            )
            incomplete = profile_status(root)
            self.assertFalse(incomplete["ready"])
            self.assertEqual(
                incomplete["user_profile"]["unresolved_followups"], 1
            )

            (local / "user_profile.md").write_text(
                "- Interview status: ready\n", encoding="utf-8"
            )
            complete = profile_status(root)
            self.assertTrue(complete["ready"])

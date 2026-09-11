import re
import unittest
from pathlib import Path


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
        from scripts.mcp_launcher import virtualenv_python

        with self.subTest("Windows layout"):
            import tempfile

            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                python = root / ".venv" / "Scripts" / "python.exe"
                python.parent.mkdir(parents=True)
                python.touch()
                self.assertEqual(virtualenv_python(root), python)

    def test_privacy_scan_passes_for_tracked_files(self):
        from scripts.privacy_scan import scan

        self.assertEqual(scan(), [])


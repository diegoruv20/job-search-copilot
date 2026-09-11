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
        ]
        self.assertEqual([str(path) for path in required if not path.is_file()], [])

    def test_skill_frontmatter_has_name_and_description(self):
        for skill_path in (ROOT / ".github" / "skills").glob("*/SKILL.md"):
            text = skill_path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill_path)
            frontmatter = text.split("---", 2)[1]
            self.assertRegex(frontmatter, r"(?m)^name: [a-z0-9-]+$")
            self.assertRegex(frontmatter, r"(?m)^description: .+$")

    def test_repository_contains_no_known_private_identifiers(self):
        prohibited = [
            "ruvalcaba",
            "diegoruv",
            "application_tracker_2026",
            "g:\\\\my drive\\\\personal",
        ]
        text_files = []
        for path in ROOT.rglob("*"):
            if (
                path.is_file()
                and ".git" not in path.parts
                and path != Path(__file__).resolve()
                and path.suffix.lower()
                in {".py", ".md", ".json", ".html", ".css", ".js", ".txt"}
            ):
                text_files.append(path)

        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore") for path in text_files
        ).lower()
        for value in prohibited:
            self.assertNotIn(value.lower(), combined)

import re
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class RepositoryCustomizationTestCase(unittest.TestCase):
    def test_required_customization_files_exist(self):
        required = [
            ROOT / ".github" / "copilot-instructions.md",
            ROOT / ".github" / "mcp.json",
            ROOT / ".codex" / "config.toml",
            ROOT / ".gemini" / "settings.json",
            ROOT / ".mcp.json",
            ROOT / "CLAUDE.md",
            ROOT / "GEMINI.md",
            ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
            ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
            ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
            ROOT / ".github" / "workflows" / "validate.yml",
            ROOT / ".github" / "skills" / "job-search" / "SKILL.md",
            ROOT / ".github" / "skills" / "resume-making" / "SKILL.md",
            ROOT / ".github" / "skills" / "application-tracking" / "SKILL.md",
            ROOT / ".github" / "skills" / "outreach" / "SKILL.md",
            ROOT / ".github" / "skills" / "interview-prep" / "SKILL.md",
            ROOT / ".github" / "skills" / "profile-onboarding" / "SKILL.md",
            ROOT / ".github" / "skills" / "safe-customization" / "SKILL.md",
            ROOT / ".github" / "agents" / "career-discovery.agent.md",
            ROOT / ".github" / "agents" / "job-search.agent.md",
            ROOT / ".github" / "agents" / "application-strategist.agent.md",
            ROOT / ".github" / "agents" / "interview-coach.agent.md",
            ROOT / ".github" / "agents" / "product-customizer.agent.md",
            ROOT / "config" / "user_profile.example.md",
            ROOT / "config" / "experience_inventory.example.md",
            ROOT / "config" / "mcp.windows.json",
            ROOT / "config" / "mcp.posix.json",
            ROOT / "job_search_copilot" / "__init__.py",
            ROOT / "job_search_copilot" / "api.py",
            ROOT / "job_search_copilot" / "data_portability.py",
            ROOT / "job_search_copilot" / "models.py",
            ROOT / "job_search_copilot" / "services.py",
            ROOT / "job_search_copilot" / "views.py",
            ROOT / "job_search_copilot" / "workspace.py",
            ROOT / "scripts" / "bootstrap.py",
            ROOT / "scripts" / "mcp_launcher.py",
            ROOT / "scripts" / "mcp_launcher.js",
            ROOT / "scripts" / "mcp_smoke.py",
            ROOT / "scripts" / "privacy_scan.py",
            ROOT / "scripts" / "release_check.py",
            ROOT / "docs" / "architecture.md",
            ROOT / "docs" / "agents.md",
            ROOT / "docs" / "workflows.md",
            ROOT / "docs" / "data-and-privacy.md",
            ROOT / "docs" / "troubleshooting.md",
            ROOT / "docs" / "profile-onboarding.md",
            ROOT / "docs" / "customization.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "LICENSE",
            ROOT / "SECURITY.md",
        ]
        self.assertEqual([str(path) for path in required if not path.is_file()], [])
        moved_root_modules = [
            "api.py",
            "data_portability.py",
            "models.py",
            "services.py",
            "views.py",
            "workspace.py",
        ]
        self.assertEqual(
            [name for name in moved_root_modules if (ROOT / name).exists()],
            [],
        )

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

    def test_node_mcp_launcher_is_cross_platform(self):
        import tempfile

        script = (
            "const launcher = require('./scripts/mcp_launcher.js');"
            "console.log(launcher.virtualenvPython(process.argv[1]));"
        )
        for relative_python in [
            Path(".venv") / "Scripts" / "python.exe",
            Path(".venv") / "bin" / "python",
        ]:
            with self.subTest(relative_python=relative_python):
                with tempfile.TemporaryDirectory() as directory:
                    python = Path(directory) / relative_python
                    python.parent.mkdir(parents=True)
                    python.touch()
                    result = subprocess.run(
                        ["node", "-e", script, directory],
                        cwd=ROOT,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        Path(result.stdout.strip()).resolve(),
                        python.resolve(),
                    )

    def test_privacy_scan_passes_for_tracked_files(self):
        from scripts.privacy_scan import scan

        self.assertEqual(scan(), [])

    def test_privacy_scan_includes_git_history(self):
        from scripts.privacy_scan import historical_blobs

        blobs = historical_blobs()
        self.assertTrue(blobs)
        self.assertTrue(
            any(path == Path("scripts/privacy_scan.py") for _, path in blobs)
        )

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
        self.assertEqual(servers["job-search-copilot"]["command"], "node")
        self.assertEqual(
            servers["job-search-copilot"]["args"],
            ["scripts/mcp_launcher.js"],
        )
        self.assertEqual(servers["playwright"]["command"], "npx")
        self.assertEqual(
            servers["playwright"]["args"],
            ["@playwright/mcp@0.0.80"],
        )

        for portable_name in ["mcp.windows.json", "mcp.posix.json"]:
            portable = json.loads(
                (ROOT / "config" / portable_name).read_text(encoding="utf-8")
            )["mcpServers"]
            self.assertEqual(portable["job-search-copilot"]["command"], "node")
            self.assertEqual(
                portable["job-search-copilot"]["args"],
                ["scripts/mcp_launcher.js"],
            )
            self.assertEqual(
                portable["playwright"]["args"],
                servers["playwright"]["args"],
            )

    def test_core_four_agent_adapters_share_contract_and_mcp_servers(self):
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        gemini = (ROOT / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("`AGENTS.md`", claude)
        self.assertIn("@./AGENTS.md", gemini)

        json_configs = [
            ROOT / ".github" / "mcp.json",
            ROOT / ".mcp.json",
            ROOT / ".gemini" / "settings.json",
        ]
        for config_path in json_configs:
            servers = json.loads(config_path.read_text(encoding="utf-8"))[
                "mcpServers"
            ]
            self.assertEqual(
                set(servers), {"job-search-copilot", "playwright"}, config_path
            )
            self.assertEqual(
                servers["job-search-copilot"]["command"], "node", config_path
            )
            self.assertEqual(
                servers["job-search-copilot"]["args"],
                ["scripts/mcp_launcher.js"],
                config_path,
            )

        codex = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.job-search-copilot]", codex)
        self.assertIn("[mcp_servers.playwright]", codex)
        self.assertIn('command = "node"', codex)
        self.assertIn('args = ["scripts/mcp_launcher.js"]', codex)

    def test_agent_contract_and_workflows_are_portable(self):
        agent_guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        copilot = (
            ROOT / ".github" / "copilot-instructions.md"
        ).read_text(encoding="utf-8")
        agent_docs = (ROOT / "docs" / "agents.md").read_text(encoding="utf-8")
        workflows = (ROOT / "docs" / "workflows.md").read_text(encoding="utf-8")

        self.assertIn("vendor-neutral operating contract", agent_guide)
        self.assertIn("Follow the complete vendor-neutral", copilot)
        self.assertIn("MCP-capable coding agent", agent_docs)
        for skill in [
            "profile-onboarding",
            "job-search",
            "resume-making",
            "application-tracking",
            "outreach",
            "interview-prep",
            "safe-customization",
        ]:
            path = f".github/skills/{skill}/SKILL.md"
            self.assertIn(path, agent_guide)
            self.assertIn(path, workflows)

    def test_profile_readiness_requires_completed_interviews(self):
        import tempfile

        from job_search_copilot.workspace import profile_status

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

    def test_customization_workflow_requires_safety_gate(self):
        instructions = (
            ROOT / ".github" / "skills" / "safe-customization" / "SKILL.md"
        ).read_text(encoding="utf-8")
        agent = (
            ROOT / ".github" / "agents" / "product-customizer.agent.md"
        ).read_text(encoding="utf-8")

        for required_rule in [
            "job_search_copilot/services.py",
            "verified online backup",
            "idempotent upgrade path",
            "scripts\\release_check.py",
            "Playwright",
        ]:
            self.assertIn(required_rule, instructions)

        self.assertIn("Always load the `safe-customization` skill", agent)
        self.assertIn("Existing user data must remain readable", agent)
        self.assertIn("the work as incomplete", agent)

    def test_contribution_workflow_separates_shared_and_personal_changes(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        agent_guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        workflow = (
            ROOT / ".github" / "workflows" / "validate.yml"
        ).read_text(encoding="utf-8")

        for classification in [
            "Universal fix",
            "Shared feature",
            "Personal customization",
        ]:
            self.assertIn(classification, contributing)

        self.assertIn("Never push directly to `main`", agent_guide)
        self.assertIn("pull_request:", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("python scripts/release_check.py", workflow)

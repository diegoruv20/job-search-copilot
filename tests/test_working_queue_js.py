import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkingQueueJavaScriptTestCase(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is not available")
    def test_queue_state_regressions(self):
        subprocess.run(
            ["node", "tests/js/working_queue_state.test.js"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_dashboard_uses_latest_request_guards_on_success_and_error(self):
        script = (ROOT / "static" / "js" / "dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(
            script.count("if (!jobRequestSequence.isCurrent(requestId))"),
            2,
        )
        self.assertIn("WorkingQueueState.TEXT_DEBOUNCE_MS", script)
        self.assertIn('window.addEventListener("pagehide"', script)
        self.assertIn("WorkingQueueState.clear(queueSessionStorage())", script)

import asyncio
import os
import tempfile
import unittest

from mcp import Client


class TrackerMcpTestCase(unittest.TestCase):
    def setUp(self):
        self.database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database.close()
        self.previous_database = os.environ.get("JOB_TRACKER_DATABASE_PATH")
        os.environ["JOB_TRACKER_DATABASE_PATH"] = self.database.name

    def tearDown(self):
        if self.previous_database is None:
            os.environ.pop("JOB_TRACKER_DATABASE_PATH", None)
        else:
            os.environ["JOB_TRACKER_DATABASE_PATH"] = self.previous_database
        os.unlink(self.database.name)

    def run_async(self, callback):
        return asyncio.run(callback())

    def test_mcp_tools_share_the_tracker_service_layer(self):
        async def scenario():
            from mcp_server import mcp

            async with Client(mcp, raise_exceptions=True) as client:
                tools = await client.list_tools()
                tool_names = {tool.name for tool in tools.tools}
                self.assertIn("job_create", tool_names)
                self.assertIn("application_record", tool_names)
                self.assertIn("dashboard_start", tool_names)

                created = await client.call_tool(
                    "job_create",
                    {
                        "company": "Fictional Health",
                        "role": "Senior Data Engineer",
                        "status": "Ready to Apply",
                        "recommendation_tier": "Apply Next",
                        "recommendation_rank": 1,
                    },
                )
                self.assertTrue(created.structured_content["ok"])
                job_id = created.structured_content["job"]["id"]

                applied = await client.call_tool(
                    "application_record", {"job_id": job_id}
                )
                self.assertEqual(
                    applied.structured_content["job"]["status"], "Applied"
                )

                summary = await client.call_tool("stats_get", {})
                self.assertEqual(summary.structured_content["stats"]["applied"], 1)

        self.run_async(scenario)

    def test_mcp_validation_returns_actionable_errors(self):
        async def scenario():
            from mcp_server import mcp

            async with Client(mcp, raise_exceptions=True) as client:
                result = await client.call_tool(
                    "job_create",
                    {
                        "company": "Unsafe Example",
                        "role": "Engineer",
                        "url": "javascript:alert(1)",
                    },
                )
                self.assertFalse(result.structured_content["ok"])
                self.assertIn("URL must start", result.structured_content["error"])

        self.run_async(scenario)

    def test_demo_loading_is_explicit_and_non_destructive(self):
        async def scenario():
            from mcp_server import mcp

            async with Client(mcp, raise_exceptions=True) as client:
                first = await client.call_tool("tracker_demo_load", {})
                self.assertTrue(first.structured_content["ok"])
                self.assertEqual(len(first.structured_content["jobs"]), 3)

                second = await client.call_tool("tracker_demo_load", {})
                self.assertFalse(second.structured_content["ok"])
                self.assertIn("not empty", second.structured_content["error"])

        self.run_async(scenario)

    def test_dashboard_stop_requires_confirmation(self):
        async def scenario():
            from mcp_server import mcp

            async with Client(mcp, raise_exceptions=True) as client:
                result = await client.call_tool("dashboard_stop", {})
                self.assertFalse(result.structured_content["ok"])
                self.assertIn("confirm=true", result.structured_content["error"])

        self.run_async(scenario)

    def test_dashboard_lifecycle_is_managed_by_pid_file(self):
        from mcp_server import dashboard_start, dashboard_status, dashboard_stop

        started = dashboard_start()
        self.assertTrue(started["ok"], started)
        self.assertTrue(started["healthy"])
        self.assertIsInstance(started["pid"], int)

        status = dashboard_status()
        self.assertTrue(status["healthy"])
        self.assertEqual(status["pid"], started["pid"])

        stopped = dashboard_stop(confirm=True)
        self.assertTrue(stopped["ok"], stopped)
        self.assertTrue(stopped["stopped"])

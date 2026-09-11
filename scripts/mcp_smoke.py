import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import Client, StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "application_record",
    "dashboard_start",
    "dashboard_status",
    "dashboard_stop",
    "followups_due",
    "history_get",
    "job_create",
    "job_delete",
    "job_get",
    "job_list",
    "job_update",
    "outcome_record",
    "profile_status",
    "recommendations_get",
    "stats_get",
    "tracker_backup",
    "tracker_demo_load",
    "tracker_export",
    "tracker_import",
    "tracker_initialize",
    "tracker_restore",
}


async def smoke():
    database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    database.close()
    environment = os.environ.copy()
    environment["JOB_TRACKER_DATABASE_PATH"] = database.name
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=str(ROOT),
        env=environment,
    )
    try:
        async with Client(parameters, raise_exceptions=True) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            missing = EXPECTED_TOOLS - names
            if missing:
                raise RuntimeError(f"Missing MCP tools: {sorted(missing)}")

            initialized = await client.call_tool("tracker_initialize", {})
            if not initialized.structured_content["ok"]:
                raise RuntimeError(initialized.structured_content)
            created = await client.call_tool(
                "job_create",
                {
                    "company": "Fictional Release Labs",
                    "role": "Platform Engineer",
                    "status": "Ready to Apply",
                    "recommendation_tier": "Apply Next",
                    "recommendation_rank": 1,
                },
            )
            if not created.structured_content["ok"]:
                raise RuntimeError(created.structured_content)
            listed = await client.call_tool("job_list", {})
            if len(listed.structured_content["jobs"]) != 1:
                raise RuntimeError("MCP-created job was not returned by job_list")
    finally:
        Path(database.name).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(smoke())
    print(f"MCP stdio smoke passed with {len(EXPECTED_TOOLS)} tools.")

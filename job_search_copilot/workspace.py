import sys
import re
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _document_status(path, template):
    if not path.is_file():
        return {
            "path": str(path),
            "exists": False,
            "template": str(template),
            "interview_status": "missing",
            "unresolved_followups": 0,
        }

    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^- Interview status:\s*(.+?)\s*$", text)
    interview_status = match.group(1).strip().lower() if match else "unknown"
    unresolved = len(re.findall(r"(?m)^-\s+\[Needs follow-up\]", text))
    return {
        "path": str(path),
        "exists": True,
        "template": str(template),
        "interview_status": interview_status,
        "unresolved_followups": unresolved,
    }


def profile_status(root=ROOT):
    root = Path(root)
    profile = root / "local" / "user_profile.md"
    experience = root / "local" / "experience_inventory.md"
    profile_document = _document_status(
        profile, root / "config" / "user_profile.example.md"
    )
    experience_document = _document_status(
        experience, root / "config" / "experience_inventory.example.md"
    )
    documents = [profile_document, experience_document]
    ready = all(
        document["exists"]
        and document["interview_status"] == "ready"
        and document["unresolved_followups"] == 0
        for document in documents
    )
    if not all(document["exists"] for document in documents):
        next_action = (
            "Run the bootstrap or copy the templates, then start the guided "
            "career-discovery interview."
        )
    elif not ready:
        next_action = (
            "Resume the career-discovery interview. Ask three to five simple "
            "questions, update both files after each round, and finish with a "
            "validation playback."
        )
    else:
        next_action = (
            "The profile is ready. Revisit the interview when goals change or new "
            "experience, outcomes, or recruiter feedback becomes available."
        )
    return {
        "ready": ready,
        "user_profile": profile_document,
        "experience_inventory": experience_document,
        "next_action": next_action,
        "guide": str(root / "docs" / "profile-onboarding.md"),
    }


def workspace_status(app, root=ROOT):
    root = Path(root)
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_path = database_uri.removeprefix("sqlite:///")
    mcp_path = root / ".github" / "mcp.json"
    try:
        mcp_servers = json.loads(mcp_path.read_text(encoding="utf-8")).get(
            "mcpServers", {}
        )
    except (FileNotFoundError, json.JSONDecodeError):
        mcp_servers = {}
    checks = {
        "python_supported": sys.version_info >= (3, 10),
        "mcp_configured": "job-search-copilot" in mcp_servers,
        "playwright_mcp_configured": "playwright" in mcp_servers,
        "node_available": bool(shutil.which("node") and shutil.which("npx")),
        "database_exists": Path(database_path).is_file(),
        "profile_ready": profile_status(root)["ready"],
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "python": sys.version.split()[0],
        "database": database_path,
        "dashboard": "http://127.0.0.1:5050",
        "profile": profile_status(root),
    }

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def profile_status(root=ROOT):
    root = Path(root)
    profile = root / "local" / "user_profile.md"
    experience = root / "local" / "experience_inventory.md"
    return {
        "ready": profile.is_file() and experience.is_file(),
        "user_profile": {
            "path": str(profile),
            "exists": profile.is_file(),
            "template": str(root / "config" / "user_profile.example.md"),
        },
        "experience_inventory": {
            "path": str(experience),
            "exists": experience.is_file(),
            "template": str(root / "config" / "experience_inventory.example.md"),
        },
    }


def workspace_status(app, root=ROOT):
    root = Path(root)
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_path = database_uri.removeprefix("sqlite:///")
    checks = {
        "python_supported": sys.version_info >= (3, 10),
        "mcp_configured": (root / ".github" / "mcp.json").is_file(),
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

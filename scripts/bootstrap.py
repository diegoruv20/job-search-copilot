import argparse
import json
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
TOTAL_STEPS = 7
MINIMUM_NODE_MAJOR = 18


def announce(message=""):
    print(message, flush=True)


def start_step(number, title, detail):
    announce()
    announce(f"[{number}/{TOTAL_STEPS}] {title}")
    announce(f"      {detail}")


def finish_step(message):
    announce(f"      [OK] {message}")


def skip_step(message):
    announce(f"      [SKIP] {message}")


def environment_python():
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def check_playwright_prerequisites():
    node = shutil.which("node")
    npx = shutil.which("npx")
    if not node or not npx:
        raise OSError(
            "Playwright MCP requires Node.js and npx. Install the current Node.js "
            "LTS release from https://nodejs.org/, reopen the terminal, and retry."
        )
    result = run([node, "--version"], capture=True)
    version = result.stdout.strip().lstrip("v")
    try:
        major = int(version.split(".", 1)[0])
    except ValueError as exc:
        raise OSError(f"Could not determine the installed Node.js version: {version}") from exc
    if major < MINIMUM_NODE_MAJOR:
        raise OSError(
            f"Playwright MCP requires Node.js {MINIMUM_NODE_MAJOR} or newer; "
            f"found {version}. Upgrade Node.js and retry."
        )
    return version


def run(command, capture=False):
    try:
        return subprocess.run(
            [str(part) for part in command],
            cwd=ROOT,
            check=True,
            capture_output=capture,
            text=capture,
        )
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            announce(exc.stdout.rstrip())
        if exc.stderr:
            announce(exc.stderr.rstrip())
        raise


def show_readiness(result):
    payload = json.loads(result.stdout)
    checks = payload["checks"]
    profile = payload["profile"]
    for label, key in (
        ("Python version supported", "python_supported"),
        ("Tracker MCP configured", "mcp_configured"),
        ("Playwright MCP configured", "playwright_mcp_configured"),
        ("Node.js and npx available", "node_available"),
        ("Local database available", "database_exists"),
        ("Career interview complete", "profile_ready"),
    ):
        state = "READY" if checks[key] else "ACTION NEEDED"
        announce(f"      [{state}] {label}")
    announce(f"      Database: {payload['database']}")
    announce(f"      Next action: {profile['next_action']}")


def copy_private_templates():
    local = ROOT / "local"
    local.mkdir(exist_ok=True)
    copies = [
        (
            ROOT / "config" / "user_profile.example.md",
            local / "user_profile.md",
        ),
        (
            ROOT / "config" / "experience_inventory.example.md",
            local / "experience_inventory.md",
        ),
    ]
    created = []
    preserved = []
    for source, destination in copies:
        if not destination.exists():
            shutil.copyfile(source, destination)
            created.append(destination)
        else:
            preserved.append(destination)
    return created, preserved


def bootstrap(load_demo=False, run_tests=True, create_profiles=True):
    announce("=" * 66)
    announce("Job Search Copilot setup")
    announce("Your database, profile, and application materials stay local.")
    announce("=" * 66)

    start_step(
        1,
        "Checking prerequisites and preparing Python",
        "Verifying Node.js for Playwright MCP and creating or reusing .venv.",
    )
    node_version = check_playwright_prerequisites()
    announce(f"      [READY] Node.js {node_version} and npx are available.")
    if not environment_python().is_file():
        venv.EnvBuilder(with_pip=True).create(VENV)
        finish_step(f"Created virtual environment at {VENV}")
    else:
        finish_step(f"Reusing existing virtual environment at {VENV}")

    python = environment_python()

    start_step(
        2,
        "Installing dependencies",
        "Installing the dashboard, database, MCP, and export packages.",
    )
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "-r",
            "requirements.txt",
        ]
    )
    finish_step("Dependencies are installed.")

    start_step(
        3,
        "Initializing the tracker",
        "Creating or safely upgrading the local SQLite database.",
    )
    run([python, "tracker_cli.py", "init"], capture=True)
    finish_step("The local tracker database is ready.")

    start_step(
        4,
        "Preparing private profile files",
        "Creating local interview templates without overwriting existing answers.",
    )
    if create_profiles:
        created, preserved = copy_private_templates()
        if created:
            finish_step(
                "Created: " + ", ".join(str(path.relative_to(ROOT)) for path in created)
            )
        if preserved:
            announce(
                "      [KEEP] Existing files were not changed: "
                + ", ".join(str(path.relative_to(ROOT)) for path in preserved)
            )
        if not created and preserved:
            finish_step("Existing private profile files are ready to reuse.")
    else:
        skip_step("Profile template creation was disabled.")

    start_step(
        5,
        "Loading optional demonstration data",
        "Demo jobs are fictional and are never loaded unless requested.",
    )
    if load_demo:
        run([python, "tracker_cli.py", "demo"])
        finish_step("Fictional demonstration jobs were loaded.")
    else:
        skip_step("Starting with a blank tracker.")

    start_step(
        6,
        "Running automated checks",
        "Verifying tracker behavior, MCP tools, privacy rules, and portability.",
    )
    if run_tests:
        run([python, "-m", "unittest", "discover", "-s", "tests", "-v"])
        finish_step("All automated tests passed.")
    else:
        skip_step("Tests were disabled with --skip-tests.")

    start_step(
        7,
        "Checking readiness",
        "Reporting database, MCP, and guided profile-interview status.",
    )
    readiness = run([python, "tracker_cli.py", "doctor"], capture=True)
    show_readiness(readiness)
    finish_step("Setup checks completed.")

    announce()
    announce("=" * 66)
    announce("Setup complete")
    announce("Next:")
    announce("  1. Start Copilot CLI from this repository.")
    announce("  2. Trust the folder and confirm both MCP servers in /mcp.")
    announce("  3. Ask the career-discovery agent to interview you.")
    announce("  4. Start the dashboard at http://127.0.0.1:5050 when needed.")
    announce("=" * 66)


def build_parser():
    parser = argparse.ArgumentParser(description="Set up Job Search Copilot locally")
    parser.add_argument("--demo", action="store_true", help="Load fictional demo jobs")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--no-profile-templates", action="store_true")
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    try:
        bootstrap(
            load_demo=arguments.demo,
            run_tests=not arguments.skip_tests,
            create_profiles=not arguments.no_profile_templates,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        announce()
        announce("[ERROR] Setup stopped before completion.")
        announce(f"        {exc}")
        announce("        Fix the reported issue, then run setup again.")
        raise SystemExit(1) from exc

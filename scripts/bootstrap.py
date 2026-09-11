import argparse
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def environment_python():
    if sys.platform == "win32":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(command):
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


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
    for source, destination in copies:
        if not destination.exists():
            shutil.copyfile(source, destination)


def bootstrap(load_demo=False, run_tests=True, create_profiles=True):
    if not environment_python().is_file():
        venv.EnvBuilder(with_pip=True).create(VENV)

    python = environment_python()
    run([python, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"])
    run([python, "tracker_cli.py", "init"])
    if create_profiles:
        copy_private_templates()
    if load_demo:
        run([python, "tracker_cli.py", "demo"])
    if run_tests:
        run([python, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([python, "tracker_cli.py", "doctor"])


def build_parser():
    parser = argparse.ArgumentParser(description="Set up Job Search Copilot locally")
    parser.add_argument("--demo", action="store_true", help="Load fictional demo jobs")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--no-profile-templates", action="store_true")
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    bootstrap(
        load_demo=arguments.demo,
        run_tests=not arguments.skip_tests,
        create_profiles=not arguments.no_profile_templates,
    )

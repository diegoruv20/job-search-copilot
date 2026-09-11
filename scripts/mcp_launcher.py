import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def virtualenv_python(root=ROOT):
    candidates = [
        Path(root) / ".venv" / "Scripts" / "python.exe",
        Path(root) / ".venv" / "bin" / "python",
    ]
    return next((path for path in candidates if path.is_file()), None)


def main(root=ROOT):
    root = Path(root)
    python = virtualenv_python(root)
    if python is None:
        raise SystemExit(
            "Job Search Copilot is not set up. Run "
            "`python scripts/bootstrap.py` from the repository root."
        )
    result = subprocess.run(
        [str(python), str(root / "mcp_server.py")],
        cwd=root,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

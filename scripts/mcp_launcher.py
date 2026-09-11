import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def virtualenv_python(root=ROOT):
    candidates = [
        Path(root) / ".venv" / "Scripts" / "python.exe",
        Path(root) / ".venv" / "bin" / "python",
    ]
    return next((path for path in candidates if path.is_file()), None)


def main():
    python = virtualenv_python()
    if python is None:
        raise SystemExit(
            "Job Search Copilot is not set up. Run "
            "`python scripts/bootstrap.py` from the repository root."
        )
    os.chdir(ROOT)
    os.execv(str(python), [str(python), str(ROOT / "mcp_server.py")])


if __name__ == "__main__":
    main()

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(command):
    subprocess.run([str(part) for part in command], cwd=ROOT, check=True)


if __name__ == "__main__":
    run([sys.executable, "scripts/privacy_scan.py"])
    run([sys.executable, "-m", "compileall", "-q", "."])
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "scripts/mcp_smoke.py"])
    node = shutil.which("node")
    if node:
        run([node, "--check", "static/js/dashboard.js"])
    print("Release checks passed.")

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIRECTORIES = {"instance", "local", "backups", "exports", "runtime"}
PRIVATE_SUFFIXES = {".db", ".db-shm", ".db-wal", ".docx", ".pdf"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".txt",
}


def tracked_files(root=ROOT):
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\0")
        if item
    ]


def scan(root=ROOT):
    root = Path(root)
    violations = []
    absolute_path_pattern = re.compile(
        r"(?:[A-Za-z]:\\Users\\|[A-Za-z]:\\My Drive\\Personal\\)",
        re.IGNORECASE,
    )
    optional_markers = [
        item.strip().lower()
        for item in os.environ.get("JOB_SEARCH_PRIVATE_MARKERS", "").split(",")
        if item.strip()
    ]

    for relative in tracked_files(root):
        if relative.parts and relative.parts[0].lower() in PRIVATE_DIRECTORIES:
            violations.append(f"private directory is tracked: {relative}")
        if relative.suffix.lower() in PRIVATE_SUFFIXES:
            violations.append(f"private artifact is tracked: {relative}")

        path = root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if absolute_path_pattern.search(text):
            violations.append(f"private absolute path in {relative}")
        lowered = text.lower()
        for marker in optional_markers:
            if marker in lowered:
                violations.append(f"private marker in {relative}: {marker}")

    return sorted(set(violations))


if __name__ == "__main__":
    failures = scan()
    if failures:
        raise SystemExit("\n".join(failures))
    print("Privacy scan passed.")

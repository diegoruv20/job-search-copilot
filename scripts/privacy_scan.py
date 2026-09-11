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


def historical_blobs(root=ROOT):
    result = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    blobs = []
    for line in result.stdout.splitlines():
        object_id, separator, relative = line.partition(" ")
        if separator and relative:
            blobs.append((object_id, Path(relative)))
    return blobs


def _private_markers():
    return [
        item.strip().lower()
        for item in os.environ.get("JOB_SEARCH_PRIVATE_MARKERS", "").split(",")
        if item.strip()
    ]


def _check_path(relative, label):
    violations = []
    if relative.parts and relative.parts[0].lower() in PRIVATE_DIRECTORIES:
        violations.append(f"private directory is {label}: {relative}")
    if relative.suffix.lower() in PRIVATE_SUFFIXES:
        violations.append(f"private artifact is {label}: {relative}")
    return violations


def _check_text(text, relative, label, absolute_path_pattern, optional_markers):
    violations = []
    if absolute_path_pattern.search(text):
        violations.append(f"private absolute path in {label} {relative}")
    lowered = text.lower()
    for marker in optional_markers:
        if marker in lowered:
            violations.append(f"private marker in {label} {relative}: {marker}")
    return violations


def scan(root=ROOT, include_history=True):
    root = Path(root)
    violations = []
    absolute_path_pattern = re.compile(
        r"(?:[A-Za-z]:\\Users\\|[A-Za-z]:\\My Drive\\Personal\\)",
        re.IGNORECASE,
    )
    optional_markers = _private_markers()

    for relative in tracked_files(root):
        violations.extend(_check_path(relative, "tracked"))

        path = root / relative
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        violations.extend(
            _check_text(
                text,
                relative,
                "tracked file",
                absolute_path_pattern,
                optional_markers,
            )
        )

    if include_history:
        seen_objects = set()
        for object_id, relative in historical_blobs(root):
            violations.extend(_check_path(relative, "present in Git history"))
            if (
                relative.suffix.lower() not in TEXT_SUFFIXES
                or object_id in seen_objects
            ):
                continue
            seen_objects.add(object_id)
            result = subprocess.run(
                ["git", "cat-file", "-p", object_id],
                cwd=root,
                check=True,
                capture_output=True,
            )
            text = result.stdout.decode("utf-8", errors="ignore")
            violations.extend(
                _check_text(
                    text,
                    relative,
                    "Git history",
                    absolute_path_pattern,
                    optional_markers,
                )
            )

    return sorted(set(violations))


if __name__ == "__main__":
    failures = scan()
    if failures:
        raise SystemExit("\n".join(failures))
    print("Privacy scan passed.")

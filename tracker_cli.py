import argparse
import json

from app import create_app
from data_portability import (
    backup_database,
    export_json,
    import_json,
    load_demo,
    restore_database,
)
from services import stats


def run_command(args):
    app = create_app()
    with app.app_context():
        if args.command == "init":
            return {"database": app.config["SQLALCHEMY_DATABASE_URI"], "stats": stats()}
        if args.command == "demo":
            return load_demo(replace=args.replace)
        if args.command == "backup":
            return {"backup": str(backup_database(args.destination))}
        if args.command == "restore":
            return restore_database(args.source, confirm=args.confirm)
        if args.command == "export":
            return {"export": str(export_json(args.destination))}
        if args.command == "import":
            return import_json(args.source, replace=args.replace)
    raise ValueError(f"Unknown command: {args.command}")


def build_parser():
    parser = argparse.ArgumentParser(description="Manage local Job Search Copilot data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create or upgrade an empty local database")

    demo = subparsers.add_parser("demo", help="Load fictional demonstration jobs")
    demo.add_argument("--replace", action="store_true")

    backup = subparsers.add_parser("backup", help="Create an online SQLite backup")
    backup.add_argument("--destination")

    restore = subparsers.add_parser("restore", help="Restore a SQLite backup")
    restore.add_argument("source")
    restore.add_argument("--confirm", action="store_true")

    export = subparsers.add_parser("export", help="Export tracker data as JSON")
    export.add_argument("--destination")

    import_parser = subparsers.add_parser("import", help="Import tracker JSON")
    import_parser.add_argument("source")
    import_parser.add_argument("--replace", action="store_true")
    return parser


if __name__ == "__main__":
    print(json.dumps(run_command(build_parser().parse_args()), indent=2, default=str))

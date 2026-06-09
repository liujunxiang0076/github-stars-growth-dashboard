from __future__ import annotations

import argparse

from github_stars_dashboard.collect import collect_candidates
from github_stars_dashboard.config import load_config
from github_stars_dashboard.pipeline import run_pipeline
from github_stars_dashboard.reports import generate_daily_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-stars-dashboard",
        description="Generate GitHub Stars growth reports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run collection, analysis, and rendering.")
    run_parser.add_argument(
        "--config",
        default="config/sources.yml",
        help="Path to the YAML config file.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and planned steps without calling external APIs.",
    )

    collect_parser = subparsers.add_parser("collect", help="Collect GitHub repository snapshots.")
    collect_parser.add_argument(
        "--config",
        default="config/sources.yml",
        help="Path to the YAML config file.",
    )

    report_parser = subparsers.add_parser("report", help="Generate reports from saved snapshots.")
    report_parser.add_argument(
        "--config",
        default="config/sources.yml",
        help="Path to the YAML config file.",
    )
    report_parser.add_argument(
        "--start-date",
        help="Start snapshot date in YYYY-MM-DD format. Defaults to yesterday.",
    )
    report_parser.add_argument(
        "--end-date",
        help="End snapshot date in YYYY-MM-DD format. Defaults to today.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "run":
        run_pipeline(config_path=args.config, dry_run=args.dry_run)
    elif args.command == "collect":
        collect_candidates(load_config(args.config))
    elif args.command == "report":
        from datetime import date

        generate_daily_report(
            load_config(args.config),
            start_date=date.fromisoformat(args.start_date) if args.start_date else None,
            end_date=date.fromisoformat(args.end_date) if args.end_date else None,
        )


if __name__ == "__main__":
    main()

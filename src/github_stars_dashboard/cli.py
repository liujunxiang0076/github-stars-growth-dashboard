from __future__ import annotations

import argparse

from github_stars_dashboard.pipeline import run_pipeline


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

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "run":
        run_pipeline(config_path=args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

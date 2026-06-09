from __future__ import annotations

from github_stars_dashboard.collect import collect_candidates
from github_stars_dashboard.config import load_config
from github_stars_dashboard.render import render_reports
from github_stars_dashboard.storage import archive_outputs


def run_pipeline(config_path: str, dry_run: bool = False) -> None:
    config = load_config(config_path)

    if dry_run:
        print("Configuration loaded.")
        print(f"timezone={config.timezone}")
        print(f"top_n={config.top_n}")
        print(f"candidate_limit={config.candidate_limit}")
        print("Dry run complete. External APIs were not called.")
        return

    candidates = collect_candidates(config)
    outputs = render_reports(config, {"candidates": candidates})
    archive_outputs(config, outputs)

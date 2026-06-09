from __future__ import annotations

from github_stars_dashboard.config import AppConfig


def collect_candidates(config: AppConfig) -> list[dict]:
    raise NotImplementedError("GitHub candidate collection will be implemented in Phase 2.")

from __future__ import annotations

from github_stars_dashboard.config import AppConfig


def render_reports(config: AppConfig, analysis: dict) -> list[str]:
    raise NotImplementedError("HTML report rendering will be implemented in Phase 3.")

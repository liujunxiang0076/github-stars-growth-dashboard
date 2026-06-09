from __future__ import annotations

from github_stars_dashboard.config import AppConfig
from github_stars_dashboard.reports import generate_daily_report


def render_reports(config: AppConfig, analysis: dict) -> list[str]:
    report_path = generate_daily_report(config)
    return [report_path.as_posix()]

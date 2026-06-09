from __future__ import annotations

from github_stars_dashboard.config import AppConfig


def archive_outputs(config: AppConfig, outputs: list[str]) -> None:
    if not config.raw.get("storage", {}).get("r2_enabled", False):
        print("R2 archival is disabled. Local reports were kept in place.")
        return

    raise NotImplementedError("R2 archival will be implemented in Phase 5.")

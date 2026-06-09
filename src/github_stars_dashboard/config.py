from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    timezone: str
    top_n: int
    candidate_limit: int
    include_forks: bool
    include_archived: bool
    raw: dict[str, Any]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    return AppConfig(
        timezone=raw.get("timezone", "Asia/Shanghai"),
        top_n=int(raw.get("top_n", 10)),
        candidate_limit=int(raw.get("candidate_limit", 1000)),
        include_forks=bool(raw.get("include_forks", False)),
        include_archived=bool(raw.get("include_archived", False)),
        raw=raw,
    )

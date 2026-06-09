from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from github_stars_dashboard.github_api import GitHubClient


@dataclass(frozen=True)
class GrowthRow:
    rank: int
    full_name: str
    html_url: str
    stars_start: int
    stars_end: int
    stars_delta: int
    growth_rate: float
    language: str | None
    topics: list[str]
    description: str | None
    growth_source: str = "snapshot_diff"
    measurement_status: str = "ok"


def calculate_growth(
    start_snapshot: list[dict],
    end_snapshot: list[dict],
    *,
    candidates: list[dict] | None = None,
    top_n: int = 10,
) -> list[GrowthRow]:
    start_by_name = {row["full_name"]: row for row in start_snapshot}
    metadata_by_name = {row["full_name"]: row for row in candidates or []}
    rows: list[GrowthRow] = []

    for end_row in end_snapshot:
        full_name = end_row["full_name"]
        start_row = start_by_name.get(full_name)
        if not start_row:
            continue

        stars_start = int(start_row.get("stargazers_count") or 0)
        stars_end = int(end_row.get("stargazers_count") or 0)
        stars_delta = stars_end - stars_start
        metadata = metadata_by_name.get(full_name, {})

        rows.append(
            GrowthRow(
                rank=0,
                full_name=full_name,
                html_url=end_row.get("html_url") or metadata.get("html_url") or "",
                stars_start=stars_start,
                stars_end=stars_end,
                stars_delta=stars_delta,
                growth_rate=(stars_delta / stars_start) if stars_start > 0 else 0,
                language=metadata.get("language"),
                topics=metadata.get("topics") or [],
                description=metadata.get("description"),
                growth_source="snapshot_diff",
                measurement_status="ok",
            )
        )

    rows.sort(key=lambda row: (row.stars_delta, row.growth_rate, row.stars_end), reverse=True)
    ranked = rows[:top_n]
    return [
        GrowthRow(
            rank=index,
            full_name=row.full_name,
            html_url=row.html_url,
            stars_start=row.stars_start,
            stars_end=row.stars_end,
            stars_delta=row.stars_delta,
            growth_rate=row.growth_rate,
            language=row.language,
            topics=row.topics,
            description=row.description,
            growth_source=row.growth_source,
            measurement_status=row.measurement_status,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def calculate_growth_from_stargazers(
    end_snapshot: list[dict],
    *,
    candidates: list[dict] | None,
    client: GitHubClient,
    start_at: datetime,
    end_at: datetime,
    top_n: int = 10,
    candidate_limit: int = 80,
) -> list[GrowthRow]:
    metadata_by_name = {row["full_name"]: row for row in candidates or []}
    rows: list[GrowthRow] = []

    for end_row in end_snapshot[:candidate_limit]:
        full_name = end_row["full_name"]
        stars_end = int(end_row.get("stargazers_count") or 0)
        metadata = metadata_by_name.get(full_name, {})
        try:
            stars_delta = client.count_stargazers_between(
                full_name,
                total_stars=stars_end,
                start_at=start_at,
                end_at=end_at,
            )
            measurement_status = "ok"
        except RuntimeError:
            stars_delta = 0
            measurement_status = "unavailable"

        stars_start = max(0, stars_end - stars_delta)
        rows.append(
            GrowthRow(
                rank=0,
                full_name=full_name,
                html_url=end_row.get("html_url") or metadata.get("html_url") or "",
                stars_start=stars_start,
                stars_end=stars_end,
                stars_delta=stars_delta,
                growth_rate=(stars_delta / stars_start) if stars_start > 0 else 0,
                language=metadata.get("language"),
                topics=metadata.get("topics") or [],
                description=metadata.get("description"),
                growth_source="stargazers_starred_at",
                measurement_status=measurement_status,
            )
        )

    rows.sort(key=lambda row: (row.stars_delta, row.growth_rate, row.stars_end), reverse=True)
    ranked = rows[:top_n]
    return [
        GrowthRow(
            rank=index,
            full_name=row.full_name,
            html_url=row.html_url,
            stars_start=row.stars_start,
            stars_end=row.stars_end,
            stars_delta=row.stars_delta,
            growth_rate=row.growth_rate,
            language=row.language,
            topics=row.topics,
            description=row.description,
            growth_source=row.growth_source,
            measurement_status=row.measurement_status,
        )
        for index, row in enumerate(ranked, start=1)
    ]

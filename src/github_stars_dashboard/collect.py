from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from github_stars_dashboard.config import AppConfig
from github_stars_dashboard.env import load_env_file
from github_stars_dashboard.github_api import GitHubClient


def collect_candidates(config: AppConfig) -> list[dict]:
    load_env_file()
    client = GitHubClient.from_env()

    run_date = datetime.now(ZoneInfo(config.timezone)).date()
    recent_date = run_date - timedelta(days=7)
    repositories: dict[str, dict] = {}

    search_queries = config.raw.get("github", {}).get("search_queries", [])
    if not search_queries:
        raise ValueError("No GitHub search queries configured.")

    for query_template in search_queries:
        query = _prepare_query(
            query_template,
            recent_date=recent_date.isoformat(),
            include_forks=config.include_forks,
            include_archived=config.include_archived,
        )
        _collect_query(client, query, config.candidate_limit, repositories)
        if len(repositories) >= config.candidate_limit:
            break

    candidates = list(repositories.values())[: config.candidate_limit]
    _write_json(Path("data/candidates") / f"{run_date.isoformat()}.json", candidates)
    _write_json(Path("data/snapshots") / f"{run_date.isoformat()}.json", _snapshot(candidates))

    print(f"Collected {len(candidates)} candidate repositories for {run_date.isoformat()}.")
    print(f"Wrote data/candidates/{run_date.isoformat()}.json")
    print(f"Wrote data/snapshots/{run_date.isoformat()}.json")
    return candidates


def _collect_query(
    client: GitHubClient,
    query: str,
    candidate_limit: int,
    repositories: dict[str, dict],
) -> None:
    page = 1
    per_page = 100

    while len(repositories) < candidate_limit:
        result = client.search_repositories(query, page=page, per_page=per_page)
        items = result.get("items", [])
        if not items:
            return

        for item in items:
            normalized = _normalize_repository(item)
            repositories.setdefault(normalized["full_name"], normalized)
            if len(repositories) >= candidate_limit:
                break

        if len(items) < per_page or page >= 10:
            return
        page += 1


def _prepare_query(
    query_template: str,
    *,
    recent_date: str,
    include_forks: bool,
    include_archived: bool,
) -> str:
    query = query_template.replace("__RECENT_DATE__", recent_date)
    if not include_forks and "fork:" not in query:
        query = f"{query} fork:false"
    if not include_archived and "archived:" not in query:
        query = f"{query} archived:false"
    return query


def _normalize_repository(item: dict) -> dict:
    owner = item.get("owner") or {}
    return {
        "id": item.get("id"),
        "node_id": item.get("node_id"),
        "name": item.get("name"),
        "full_name": item.get("full_name"),
        "owner": owner.get("login"),
        "html_url": item.get("html_url"),
        "description": item.get("description"),
        "topics": item.get("topics") or [],
        "language": item.get("language"),
        "stargazers_count": item.get("stargazers_count") or 0,
        "forks_count": item.get("forks_count") or 0,
        "open_issues_count": item.get("open_issues_count") or 0,
        "watchers_count": item.get("watchers_count") or 0,
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "pushed_at": item.get("pushed_at"),
        "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")),
        "default_branch": item.get("default_branch"),
        "license": (item.get("license") or {}).get("spdx_id"),
    }


def _snapshot(candidates: list[dict]) -> list[dict]:
    return [
        {
            "full_name": candidate["full_name"],
            "html_url": candidate["html_url"],
            "stargazers_count": candidate["stargazers_count"],
            "forks_count": candidate["forks_count"],
            "open_issues_count": candidate["open_issues_count"],
            "pushed_at": candidate["pushed_at"],
            "updated_at": candidate["updated_at"],
        }
        for candidate in candidates
    ]


def _write_json(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

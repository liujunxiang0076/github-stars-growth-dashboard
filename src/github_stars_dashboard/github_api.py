from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"


@dataclass(frozen=True)
class GitHubClient:
    token: str | None = None

    @classmethod
    def from_env(cls) -> "GitHubClient":
        return cls(token=os.environ.get("GITHUB_TOKEN") or None)

    def search_repositories(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 100,
        sort: str = "stars",
        order: str = "desc",
    ) -> dict[str, Any]:
        params = urlencode(
            {
                "q": query,
                "sort": sort,
                "order": order,
                "page": page,
                "per_page": per_page,
            }
        )
        return self.get_json(f"{API_BASE_URL}/search/repositories?{params}")

    def get_repository_readme(self, full_name: str) -> dict[str, Any]:
        owner, repo = full_name.split("/", 1)
        return self.get_json(f"{API_BASE_URL}/repos/{quote(owner)}/{quote(repo)}/readme")

    def list_releases(self, full_name: str, *, per_page: int = 5) -> list[dict[str, Any]]:
        owner, repo = full_name.split("/", 1)
        params = urlencode({"per_page": per_page})
        result = self.get_json(f"{API_BASE_URL}/repos/{quote(owner)}/{quote(repo)}/releases?{params}")
        return result if isinstance(result, list) else []

    def list_recent_issues(self, full_name: str, *, per_page: int = 8) -> list[dict[str, Any]]:
        owner, repo = full_name.split("/", 1)
        params = urlencode({"state": "all", "sort": "updated", "direction": "desc", "per_page": per_page})
        result = self.get_json(f"{API_BASE_URL}/repos/{quote(owner)}/{quote(repo)}/issues?{params}")
        return result if isinstance(result, list) else []

    def count_stargazers_between(
        self,
        full_name: str,
        *,
        total_stars: int,
        start_at: datetime,
        end_at: datetime,
        max_pages: int = 50,
    ) -> int:
        if not self.token:
            raise RuntimeError("GitHub GraphQL stargazer scan requires GITHUB_TOKEN.")

        owner, repo = full_name.split("/", 1)
        count = 0
        cursor: str | None = None
        pages_scanned = 0

        query = """
        query($owner: String!, $name: String!, $cursor: String) {
          repository(owner: $owner, name: $name) {
            stargazers(
              first: 100
              after: $cursor
              orderBy: {field: STARRED_AT, direction: DESC}
            ) {
              edges {
                starredAt
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """

        while pages_scanned < max_pages:
            payload = self.post_graphql_with_retry(
                query,
                {"owner": owner, "name": repo, "cursor": cursor},
            )
            stargazers = payload["data"]["repository"]["stargazers"]
            edges = stargazers.get("edges") or []
            if not edges:
                break

            pages_scanned += 1
            saw_older_than_period = False
            for edge in edges:
                starred_at = edge.get("starredAt")
                if not starred_at:
                    continue
                starred = datetime.fromisoformat(starred_at.replace("Z", "+00:00"))
                if start_at <= starred < end_at:
                    count += 1
                elif starred < start_at:
                    saw_older_than_period = True

            if saw_older_than_period:
                break
            page_info = stargazers.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

        if pages_scanned >= max_pages:
            raise RuntimeError(f"Stargazer scan exceeded {max_pages} GraphQL pages for {full_name}.")
        return count

    def post_graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = Request(
            GRAPHQL_URL,
            data=body,
            headers={
                **self._headers(),
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body_text = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub GraphQL request failed with HTTP {error.code}: {body_text}") from error
        except (TimeoutError, URLError) as error:
            raise RuntimeError(f"GitHub GraphQL request failed: {error}") from error

        if payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL returned errors: {payload['errors']}")
        return payload

    def post_graphql_with_retry(
        self,
        query: str,
        variables: dict[str, Any],
        *,
        attempts: int = 3,
    ) -> dict[str, Any]:
        last_error: RuntimeError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self.post_graphql(query, variables)
            except RuntimeError as error:
                last_error = error
                if attempt == attempts:
                    break
                time.sleep(1.5 * attempt)
        raise last_error or RuntimeError("GitHub GraphQL request failed.")

    def get_json(self, url: str, *, accept: str | None = None) -> Any:
        request = Request(url, headers=self._headers(accept=accept))

        try:
            with urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code in {403, 429}:
                reset = error.headers.get("X-RateLimit-Reset")
                if reset and reset.isdigit():
                    wait_seconds = max(0, int(reset) - int(time.time()))
                    detail = f" GitHub rate limit may reset in {wait_seconds} seconds."
                else:
                    detail = ""
                raise RuntimeError(f"GitHub API rate limited or forbidden.{detail} {body}") from error
            raise RuntimeError(f"GitHub API request failed with HTTP {error.code}: {body}") from error
        except (TimeoutError, URLError) as error:
            raise RuntimeError(f"GitHub API request failed: {error}") from error

    def _headers(self, *, accept: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": accept or "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-stars-growth-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

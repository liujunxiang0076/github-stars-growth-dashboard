from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE_URL = "https://api.github.com"


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

    def get_json(self, url: str) -> dict[str, Any]:
        request = Request(url, headers=self._headers())

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

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-stars-growth-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

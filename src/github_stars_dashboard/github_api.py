from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
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

    def get_json(self, url: str) -> dict[str, Any]:
        request = Request(url, headers=self._headers())

        try:
            with urlopen(request, timeout=30) as response:
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

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-stars-growth-dashboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

from __future__ import annotations

import base64
import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

from github_stars_dashboard.config import AppConfig
from github_stars_dashboard.env import load_env_file
from github_stars_dashboard.github_api import GitHubClient
from github_stars_dashboard.growth import GrowthRow


def analyze_top_repositories(config: AppConfig, candidates: list[dict]) -> dict:
    raise NotImplementedError("Repository analysis will be implemented in Phase 4.")


def enrich_growth_rows(config: AppConfig, rows: list[GrowthRow]) -> dict[str, dict]:
    load_env_file()
    client = GitHubClient.from_env()
    analysis: dict[str, dict] = {}

    for row in rows:
        analysis[row.full_name] = analyze_repository(config, client, row)

    return analysis


def analyze_repository(config: AppConfig, client: GitHubClient, row: GrowthRow) -> dict:
    readme = _safe_readme(client, row.full_name, config)
    releases = _safe_releases(client, row.full_name)
    issues = _safe_issues(client, row.full_name)

    recent_releases = _recent_releases(releases, days=30)
    issue_signals = _issue_signals(issues)
    topics = row.topics[:8]
    readme_summary = _summarize_readme(readme)
    category = _classify_repository(row, readme_summary)
    purpose = _build_purpose_summary(row, readme_summary, category)
    likely_reasons = _build_likely_reasons(row, recent_releases, issue_signals, topics, category)
    observed_signals = _build_observed_signals(row, recent_releases, issue_signals, readme)
    confidence = _confidence(readme, recent_releases, issue_signals)

    return {
        "purpose_summary": purpose,
        "category": category,
        "observed_signals": observed_signals,
        "likely_reasons": likely_reasons,
        "evidence": {
            "readme_excerpt": readme_summary,
            "recent_releases": [
                {
                    "name": release.get("name") or release.get("tag_name"),
                    "tag_name": release.get("tag_name"),
                    "published_at": release.get("published_at"),
                    "html_url": release.get("html_url"),
                }
                for release in recent_releases[:3]
            ],
            "recent_issues": issue_signals["sample_titles"],
            "external_search": _external_search_links(row),
        },
        "confidence": confidence,
        "risk_notes": _risk_notes(readme, recent_releases),
    }


def _safe_readme(client: GitHubClient, full_name: str, config: AppConfig) -> str:
    try:
        payload = client.get_repository_readme(full_name)
    except RuntimeError:
        return ""

    encoded = payload.get("content")
    if not encoded:
        return ""

    try:
        content = base64.b64decode(encoded, validate=False).decode("utf-8", errors="replace")
    except ValueError:
        return ""

    max_chars = int(config.raw.get("analysis", {}).get("readme_max_chars", 12000))
    return content[:max_chars]


def _safe_releases(client: GitHubClient, full_name: str) -> list[dict]:
    try:
        return client.list_releases(full_name, per_page=5)
    except RuntimeError:
        return []


def _safe_issues(client: GitHubClient, full_name: str) -> list[dict]:
    try:
        return client.list_recent_issues(full_name, per_page=8)
    except RuntimeError:
        return []


def _recent_releases(releases: list[dict], *, days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for release in releases:
        published_at = release.get("published_at")
        if not published_at:
            continue
        try:
            published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if published >= cutoff:
            recent.append(release)
    return recent


def _issue_signals(issues: list[dict]) -> dict:
    pull_requests = [issue for issue in issues if "pull_request" in issue]
    plain_issues = [issue for issue in issues if "pull_request" not in issue]
    return {
        "recent_items": len(issues),
        "recent_pull_requests": len(pull_requests),
        "recent_issues": len(plain_issues),
        "sample_titles": [
            {
                "title": issue.get("title"),
                "html_url": issue.get("html_url"),
                "type": "PR" if "pull_request" in issue else "Issue",
            }
            for issue in issues[:5]
        ],
    }


def _summarize_readme(readme: str) -> str:
    if not readme:
        return ""

    text = re.sub(r"```.*?```", " ", readme, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[#>*_`~|-]+", " ", text)
    text = re.sub(r":[-a-zA-Z0-9_+]+:", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?。！？])\s+", text)
    summary = " ".join(sentence for sentence in sentences[:3] if sentence)
    return summary[:420]


def _classify_repository(row: GrowthRow, readme_summary: str) -> str:
    text = " ".join(
        [
            row.full_name,
            row.description or "",
            " ".join(row.topics),
            readme_summary,
        ]
    ).lower()

    tokens = set(re.findall(r"[a-z0-9]+", text))

    if any(keyword in text for keyword in ["awesome", "curated list", "resources", "free learning"]):
        return "curated_resource_list"
    if any(keyword in text for keyword in ["roadmap", "guide", "learning path"]):
        return "learning_roadmap"
    if any(keyword in text for keyword in ["api", "apis", "endpoint"]):
        return "api_directory"
    if tokens.intersection({"ai", "llm", "agent", "agents", "assistant", "mcp"}):
        return "ai_tooling"
    if any(keyword in text for keyword in ["framework", "library", "sdk"]):
        return "developer_library"
    return "general_project"


def _build_purpose_summary(row: GrowthRow, readme_summary: str, category: str) -> str:
    prefix_by_category = {
        "curated_resource_list": "这是一个资源索引型仓库，核心价值是把分散的工具、教程或项目筛选后集中整理，降低用户搜索和比较成本。",
        "learning_roadmap": "这是一个学习路线/知识导航型仓库，核心价值是把复杂技术栈拆成可跟随的路径、清单或指南。",
        "api_directory": "这是一个 API 目录型仓库，核心价值是帮助开发者快速发现可用接口、示例和接入入口。",
        "ai_tooling": "这是一个 AI 工具型仓库，核心价值通常集中在模型使用、智能体、自动化或开发效率提升。",
        "developer_library": "这是一个开发库/框架型仓库，核心价值是提供可复用能力，帮助开发者更快构建应用。",
        "general_project": "这是一个通用开源项目，具体价值需要结合 README、topic 和近期活动判断。",
    }
    prefix = prefix_by_category.get(category, prefix_by_category["general_project"])
    if readme_summary:
        return f"{prefix} README 摘要：{readme_summary}"
    if row.description:
        return f"{prefix} GitHub 描述：{row.description}"
    return f"{prefix} 当前缺少可用 README 摘要和描述，需要人工进一步确认用途。"


def _build_observed_signals(
    row: GrowthRow,
    recent_releases: list[dict],
    issue_signals: dict,
    readme: str,
) -> list[str]:
    signals = [f"当前 Stars 总量 {row.stars_end:,}。"]
    if row.measurement_status == "ok":
        signals.insert(0, f"昨日新增 Stars {row.stars_delta:,}，增长率 {row.growth_rate * 100:.2f}%。")
    else:
        signals.insert(0, "昨日新增 Stars 未能可靠统计，通常是 GitHub API 限流或 token 未配置导致。")
    if recent_releases:
        signals.append(f"近 30 天有 {len(recent_releases)} 个 release，说明近期存在发布动作。")
    if issue_signals["recent_items"]:
        signals.append(
            f"近期 issue/PR 更新 {issue_signals['recent_items']} 条，其中 PR "
            f"{issue_signals['recent_pull_requests']} 条。"
        )
    if readme:
        signals.append("README 可读取，项目定位和使用方式具备可分析材料。")
    return signals


def _build_likely_reasons(
    row: GrowthRow,
    recent_releases: list[dict],
    issue_signals: dict,
    topics: list[str],
    category: str,
) -> list[str]:
    reasons = []
    hot_topics = {"ai", "llm", "agent", "agents", "mcp", "rag", "workflow", "cursor"}
    topic_hits = [topic for topic in topics if topic.lower() in hot_topics]

    if recent_releases:
        release_names = ", ".join(
            release.get("name") or release.get("tag_name") or "untitled"
            for release in recent_releases[:2]
        )
        reasons.append(f"近期发布可能带来曝光，相关 release：{release_names}。")
    if topic_hits:
        reasons.append(f"仓库 topics 命中热点方向：{', '.join(topic_hits)}，可能受技术关注度推动。")
    if issue_signals["recent_pull_requests"] >= 2:
        reasons.append("近期 PR 活跃，显示维护节奏较强，容易增强用户信任。")
    if row.growth_rate >= 0.05:
        reasons.append("增长率较高，可能来自低基数项目的集中传播或新近曝光。")
    if row.stars_delta >= 100:
        reasons.append("新增 Stars 绝对值较高，可能被榜单、文章、社区讨论或产品发布放大。")
    if category == "curated_resource_list":
        reasons.append("资源清单型仓库天然适合被收藏，用户未必每天使用，但会为了后续检索和分享而 star。")
    elif category == "learning_roadmap":
        reasons.append("路线图/学习指南通常覆盖新手入门和技能规划需求，容易在搜索、课程、文章引用中持续获得曝光。")
    elif category == "api_directory":
        reasons.append("API 目录解决的是开发前期发现和选型问题，适合被工具开发者、教程作者和集成场景反复引用。")
    elif category == "ai_tooling":
        reasons.append("AI/智能体相关项目处在高关注周期，若 README 展示效果清晰，容易被开发者快速收藏试用。")
    elif category == "developer_library":
        reasons.append("库/框架类项目的增长往往来自真实集成需求、生态推荐、版本发布或迁移讨论。")
    if not reasons:
        reasons.append("当前 GitHub 侧信号有限，增长原因需要结合外部文章和社区讨论继续核验。")

    return reasons


def _external_search_links(row: GrowthRow) -> list[dict]:
    queries = [
        f"{row.full_name} GitHub",
        f"{row.full_name} release",
        f"{row.full_name} Hacker News Reddit blog",
    ]
    return [
        {
            "label": query,
            "url": f"https://www.google.com/search?q={quote_plus(query)}",
        }
        for query in queries
    ]


def _confidence(readme: str, recent_releases: list[dict], issue_signals: dict) -> str:
    score = 0
    if readme:
        score += 1
    if recent_releases:
        score += 1
    if issue_signals["recent_items"]:
        score += 1
    if score >= 3:
        return "中高"
    if score == 2:
        return "中"
    return "低"


def _risk_notes(readme: str, recent_releases: list[dict]) -> list[str]:
    notes = ["外部搜索目前以可点击检索入口呈现，尚未自动抓取第三方网页正文。"]
    if not readme:
        notes.append("README 不可用或读取失败，用途总结可能偏弱。")
    if not recent_releases:
        notes.append("未发现近 30 天 release，不代表没有通过社媒、文章或榜单传播。")
    return notes

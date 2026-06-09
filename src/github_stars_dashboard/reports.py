from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from github_stars_dashboard.config import AppConfig
from github_stars_dashboard.growth import GrowthRow, calculate_growth


def generate_daily_report(
    config: AppConfig,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Path:
    today = datetime.now(ZoneInfo(config.timezone)).date()
    resolved_end_date = end_date or today
    resolved_start_date = start_date or (resolved_end_date - timedelta(days=1))

    start_snapshot_path = Path("data/snapshots") / f"{resolved_start_date.isoformat()}.json"
    end_snapshot_path = Path("data/snapshots") / f"{resolved_end_date.isoformat()}.json"
    candidates_path = Path("data/candidates") / f"{resolved_end_date.isoformat()}.json"

    if not start_snapshot_path.exists():
        raise FileNotFoundError(
            f"Missing start snapshot: {start_snapshot_path}. "
            "Run the collector on at least two dates before generating a growth report."
        )
    if not end_snapshot_path.exists():
        raise FileNotFoundError(f"Missing end snapshot: {end_snapshot_path}.")

    start_snapshot = _read_json_list(start_snapshot_path)
    end_snapshot = _read_json_list(end_snapshot_path)
    candidates = _read_json_list(candidates_path) if candidates_path.exists() else []
    rows = calculate_growth(
        start_snapshot,
        end_snapshot,
        candidates=candidates,
        top_n=config.top_n,
    )

    report = {
        "type": "daily",
        "period_start": resolved_start_date.isoformat(),
        "period_end": resolved_start_date.isoformat(),
        "baseline_snapshot": start_snapshot_path.as_posix(),
        "ending_snapshot": end_snapshot_path.as_posix(),
        "generated_at": datetime.now(ZoneInfo(config.timezone)).isoformat(timespec="seconds"),
        "timezone": config.timezone,
        "top_n": config.top_n,
        "rows": [asdict(row) for row in rows],
    }

    analysis_path = Path("data/analysis") / f"{resolved_start_date.isoformat()}.json"
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html_path = Path("reports/daily") / f"{resolved_start_date.isoformat()}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(_render_daily_html(report, rows), encoding="utf-8")

    index_path = Path("reports/index.html")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(_render_index_html(report, html_path), encoding="utf-8")

    print(f"Generated daily report for {resolved_start_date.isoformat()}.")
    print(f"Wrote {analysis_path.as_posix()}")
    print(f"Wrote {html_path.as_posix()}")
    print(f"Wrote {index_path.as_posix()}")
    return html_path


def _read_json_list(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}.")
    return data


def _render_daily_html(report: dict, rows: list[GrowthRow]) -> str:
    title = f"GitHub Stars 增长日报 {report['period_start']}"
    rows_html = "\n".join(_render_row(row) for row in rows)
    if not rows_html:
        rows_html = """
        <tr>
          <td colspan="9" class="empty">没有可计算的增长数据。请确认起止快照中存在相同仓库。</td>
        </tr>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #667085;
      --line: #d7dce3;
      --accent: #0f766e;
      --accent-soft: #e6f4f1;
      --warn: #9a3412;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      line-height: 1.2;
      letter-spacing: 0;
    }}
    .meta {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      height: 32px;
      padding: 0 10px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      background: #eef1f5;
      color: #344054;
      font-weight: 650;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    a {{
      color: #075985;
      text-decoration: none;
      font-weight: 650;
    }}
    a:hover {{ text-decoration: underline; }}
    .rank {{ width: 56px; color: var(--muted); }}
    .repo {{ width: 220px; overflow-wrap: anywhere; }}
    .num {{ width: 104px; font-variant-numeric: tabular-nums; }}
    .delta {{
      display: inline-flex;
      padding: 2px 8px;
      background: var(--accent-soft);
      color: var(--accent);
      border-radius: 999px;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }}
    .desc {{
      color: var(--muted);
      overflow-wrap: anywhere;
    }}
    .topics {{
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
    }}
    .topic {{
      display: inline-flex;
      max-width: 100%;
      padding: 2px 6px;
      background: #f2f4f7;
      color: #475467;
      border: 1px solid #e4e7ec;
      border-radius: 999px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .note {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .empty {{
      color: var(--warn);
      text-align: center;
      padding: 28px;
    }}
    @media (max-width: 820px) {{
      header {{ display: block; }}
      .badge {{ margin-top: 12px; }}
      section {{ overflow-x: auto; }}
      table {{ min-width: 940px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{html.escape(title)}</h1>
        <p class="meta">统计周期：{html.escape(report['period_start'])} 00:00 - 23:59，时区：{html.escape(report['timezone'])}</p>
        <p class="meta">生成时间：{html.escape(report['generated_at'])}</p>
      </div>
      <div class="badge">Top {report['top_n']} by Stars Delta</div>
    </header>

    <section aria-label="GitHub Stars 增长榜">
      <table>
        <thead>
          <tr>
            <th class="rank">排名</th>
            <th class="repo">仓库</th>
            <th class="num">起始 Stars</th>
            <th class="num">结束 Stars</th>
            <th class="num">新增</th>
            <th class="num">增长率</th>
            <th>语言</th>
            <th>Topics</th>
            <th>用途摘要</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </section>

    <p class="note">数据基于本地 GitHub API 快照差值计算。首次运行需要至少两天快照才能形成真实增长榜；增长原因深度分析将在下一阶段接入 README、release、issues 和联网搜索。</p>
  </main>
</body>
</html>
"""


def _render_row(row: GrowthRow) -> str:
    topics = row.topics[:5]
    topics_html = "".join(f'<span class="topic">{html.escape(topic)}</span>' for topic in topics)
    if not topics_html:
        topics_html = '<span class="desc">-</span>'

    growth_rate = f"{row.growth_rate * 100:.2f}%"
    description = row.description or "暂无描述"
    return f"""
          <tr>
            <td class="rank">#{row.rank}</td>
            <td class="repo"><a href="{html.escape(row.html_url)}" target="_blank" rel="noreferrer">{html.escape(row.full_name)}</a></td>
            <td class="num">{row.stars_start:,}</td>
            <td class="num">{row.stars_end:,}</td>
            <td class="num"><span class="delta">+{row.stars_delta:,}</span></td>
            <td class="num">{html.escape(growth_rate)}</td>
            <td>{html.escape(row.language or "-")}</td>
            <td><div class="topics">{topics_html}</div></td>
            <td class="desc">{html.escape(description)}</td>
          </tr>
"""


def _render_index_html(report: dict, daily_path: Path) -> str:
    title = "GitHub Stars 增长看板"
    relative_daily_path = daily_path.relative_to(Path("reports")).as_posix()
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      background: #f7f8fa;
      color: #20242a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      padding: 40px 20px;
    }}
    h1 {{ margin: 0 0 12px; font-size: 30px; letter-spacing: 0; }}
    a {{
      display: inline-flex;
      margin-top: 16px;
      color: #075985;
      font-weight: 700;
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
    p {{ color: #667085; line-height: 1.6; }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>最新日报：{html.escape(report['period_start'])}，生成时间：{html.escape(report['generated_at'])}</p>
    <a href="{html.escape(relative_daily_path)}">打开最新 HTML 日报</a>
  </main>
</body>
</html>
"""

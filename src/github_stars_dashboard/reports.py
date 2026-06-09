from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from github_stars_dashboard.analyze import enrich_growth_rows
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
    row_analysis = enrich_growth_rows(config, rows)

    report = {
        "type": "daily",
        "period_start": resolved_start_date.isoformat(),
        "period_end": resolved_start_date.isoformat(),
        "baseline_snapshot": start_snapshot_path.as_posix(),
        "ending_snapshot": end_snapshot_path.as_posix(),
        "generated_at": datetime.now(ZoneInfo(config.timezone)).isoformat(timespec="seconds"),
        "timezone": config.timezone,
        "top_n": config.top_n,
        "rows": [
            {
                **asdict(row),
                "analysis": row_analysis.get(row.full_name, {}),
            }
            for row in rows
        ],
    }

    analysis_path = Path("data/analysis") / f"{resolved_start_date.isoformat()}.json"
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    html_path = Path("reports/daily") / f"{resolved_start_date.isoformat()}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(_render_daily_html(report, rows, row_analysis), encoding="utf-8")

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


def _render_daily_html(report: dict, rows: list[GrowthRow], row_analysis: dict[str, dict]) -> str:
    title = f"GitHub Stars 增长日报 {report['period_start']}"
    total_delta = sum(row.stars_delta for row in rows)
    top_growth = rows[0].stars_delta if rows else 0
    rows_html = "\n".join(_render_row(row, row_analysis.get(row.full_name, {})) for row in rows)
    cards_html = "\n".join(_render_analysis_card(row, row_analysis.get(row.full_name, {})) for row in rows)
    if not rows_html:
        rows_html = """
        <tr>
          <td colspan="10" class="empty">没有可计算的增长数据。请确认起止快照中存在相同仓库。</td>
        </tr>
        """
    if not cards_html:
        cards_html = '<p class="empty">暂无可展示的仓库分析。</p>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --paper: #f4efe6;
      --paper-strong: #ebe2d2;
      --ink: #20201d;
      --muted: #6f6a5f;
      --line: #d4c7b2;
      --panel: #fffaf0;
      --panel-2: #fbf3e4;
      --green: #137a5a;
      --green-soft: #dff0e8;
      --red: #b23a2f;
      --blue: #275b8c;
      --gold: #b7791f;
      --shadow: 0 18px 40px rgba(58, 43, 23, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        linear-gradient(rgba(32, 32, 29, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(32, 32, 29, 0.035) 1px, transparent 1px),
        var(--paper);
      background-size: 26px 26px;
      color: var(--ink);
      font-family: Georgia, "Times New Roman", "Microsoft YaHei", serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 34px 20px 56px;
    }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 28px;
      align-items: end;
      margin-bottom: 22px;
      border-bottom: 3px double var(--ink);
      padding-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 40px;
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
      justify-content: center;
      min-height: 42px;
      padding: 0 14px;
      border: 1px solid var(--ink);
      background: var(--ink);
      color: #fffaf0;
      font-size: 12px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      white-space: nowrap;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 22px 0;
    }}
    .stat {{
      border: 1px solid var(--line);
      background: rgba(255, 250, 240, 0.86);
      box-shadow: var(--shadow);
      padding: 16px;
      min-height: 104px;
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .stat strong {{
      display: block;
      margin-top: 8px;
      font-size: 28px;
      line-height: 1.15;
      font-variant-numeric: tabular-nums;
    }}
    h2 {{
      margin: 30px 0 12px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: var(--shadow);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      text-align: left;
      font-size: 14px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    th {{
      background: var(--paper-strong);
      color: #3e3427;
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    a {{
      color: var(--blue);
      text-decoration: none;
      font-weight: 650;
    }}
    a:hover {{ text-decoration: underline; }}
    .rank {{ width: 56px; color: var(--muted); font-family: Georgia, serif; }}
    .repo {{ width: 220px; overflow-wrap: anywhere; }}
    .num {{ width: 104px; font-variant-numeric: tabular-nums; }}
    .delta {{
      display: inline-flex;
      padding: 2px 8px;
      background: var(--green-soft);
      color: var(--green);
      border-radius: 999px;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }}
    .confidence {{
      display: inline-flex;
      padding: 2px 8px;
      background: #f7e7bb;
      color: #7a4d09;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
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
      background: #f2eadc;
      color: #5f5548;
      border: 1px solid #e1d2ba;
      border-radius: 999px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .note {{
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
    }}
    .analysis-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 12px;
    }}
    .analysis-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: var(--shadow);
      position: relative;
    }}
    .analysis-card::before {{
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 4px;
      background: var(--green);
      border-radius: 8px 0 0 8px;
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 10px;
    }}
    .card-head h3 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
      overflow-wrap: anywhere;
    }}
    .card-head small {{
      color: var(--muted);
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      white-space: nowrap;
    }}
    .analysis-card p {{
      margin: 10px 0;
      color: #423a31;
      font-size: 14px;
    }}
    .analysis-card h4 {{
      margin: 16px 0 8px;
      font-size: 13px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--red);
    }}
    .analysis-card ul {{
      margin: 0;
      padding-left: 18px;
      color: #4d463e;
      font-size: 14px;
    }}
    .source-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }}
    .source-links a {{
      display: inline-flex;
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--blue);
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    .empty {{
      color: var(--red);
      text-align: center;
      padding: 28px;
    }}
    @media (max-width: 820px) {{
      header {{ display: block; }}
      .badge {{ margin-top: 12px; }}
      .stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .analysis-grid {{ grid-template-columns: 1fr; }}
      section {{ overflow-x: auto; }}
      table {{ min-width: 1080px; }}
    }}
    @media (max-width: 520px) {{
      h1 {{ font-size: 30px; }}
      .stats {{ grid-template-columns: 1fr; }}
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

    <div class="stats" aria-label="日报指标概览">
      <div class="stat"><span>Tracked Top</span><strong>{len(rows)}</strong></div>
      <div class="stat"><span>Total Delta</span><strong>+{total_delta:,}</strong></div>
      <div class="stat"><span>Leader Delta</span><strong>+{top_growth:,}</strong></div>
      <div class="stat"><span>Evidence Mode</span><strong>GitHub</strong></div>
    </div>

    <h2>增长榜</h2>
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
            <th>分析置信度</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </section>

    <h2>逐仓库分析</h2>
    <div class="analysis-grid">
      {cards_html}
    </div>

    <p class="note">数据基于本地 GitHub API 快照差值计算。分析证据来自 README、近期 release、近期 issue/PR；外部搜索以可点击检索入口呈现，后续自动化可继续抓取第三方网页正文。</p>
  </main>
</body>
</html>
"""


def _render_row(row: GrowthRow, analysis: dict) -> str:
    topics = row.topics[:5]
    topics_html = "".join(f'<span class="topic">{html.escape(topic)}</span>' for topic in topics)
    if not topics_html:
        topics_html = '<span class="desc">-</span>'

    growth_rate = f"{row.growth_rate * 100:.2f}%"
    purpose = analysis.get("purpose_summary") or row.description or "暂无描述"
    confidence = analysis.get("confidence") or "低"
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
            <td class="desc">{html.escape(_clip(purpose, 160))}</td>
            <td><span class="confidence">{html.escape(confidence)}</span></td>
          </tr>
"""


def _render_analysis_card(row: GrowthRow, analysis: dict) -> str:
    purpose = analysis.get("purpose_summary") or row.description or "暂无用途摘要。"
    signals = analysis.get("observed_signals") or []
    reasons = analysis.get("likely_reasons") or []
    evidence = analysis.get("evidence") or {}
    release_links = evidence.get("recent_releases") or []
    issue_links = evidence.get("recent_issues") or []
    search_links = evidence.get("external_search") or []

    signals_html = _render_list(signals)
    reasons_html = _render_list(reasons)
    release_html = _render_links(
        [
            {
                "label": item.get("name") or item.get("tag_name") or "release",
                "url": item.get("html_url"),
            }
            for item in release_links
            if item.get("html_url")
        ]
    )
    issue_html = _render_links(
        [
            {"label": _clip(item.get("title") or item.get("type") or "issue", 36), "url": item.get("html_url")}
            for item in issue_links
            if item.get("html_url")
        ]
    )
    search_html = _render_links(search_links)

    return f"""
      <article class="analysis-card">
        <div class="card-head">
          <h3><a href="{html.escape(row.html_url)}" target="_blank" rel="noreferrer">#{row.rank} {html.escape(row.full_name)}</a></h3>
          <small>+{row.stars_delta:,} Stars</small>
        </div>
        <p>{html.escape(purpose)}</p>
        <h4>增长信号</h4>
        {signals_html}
        <h4>可能原因</h4>
        {reasons_html}
        <h4>证据入口</h4>
        <div class="source-links">
          {release_html}
          {issue_html}
          {search_html}
        </div>
      </article>
"""


def _render_list(items: list[str]) -> str:
    if not items:
        return "<p class=\"desc\">暂无足够信号。</p>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items[:5]) + "</ul>"


def _render_links(items: list[dict]) -> str:
    links = []
    for item in items[:6]:
        label = item.get("label")
        url = item.get("url")
        if not label or not url:
            continue
        links.append(
            f'<a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(_clip(label, 34))}</a>'
        )
    return "".join(links)


def _clip(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[: length - 1].rstrip() + "…"


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
      background: #f4efe6;
      color: #20201d;
      font-family: Georgia, "Times New Roman", "Microsoft YaHei", serif;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      padding: 40px 20px;
    }}
    h1 {{ margin: 0 0 12px; font-size: 34px; letter-spacing: 0; }}
    a {{
      display: inline-flex;
      margin-top: 16px;
      color: #275b8c;
      font-weight: 700;
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
    p {{ color: #6f6a5f; line-height: 1.6; }}
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

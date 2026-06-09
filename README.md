# GitHub Stars Growth Dashboard

Generate daily, weekly, and monthly HTML reports for fast-growing GitHub repositories.

The project is designed for Codex automation: a scheduled run collects candidate repositories, stores snapshots, analyzes Top 10 growth, renders static HTML reports, and can later archive outputs to Cloudflare R2.

## Stack

- Python for collection, analysis, rendering, and storage orchestration.
- Static HTML for the report dashboard.
- Local JSON snapshots as the first storage layer.
- Optional S3-compatible upload for Cloudflare R2.

## Current Status

Project skeleton is initialized. Implementation will follow `docs/prd-github-stars-growth-dashboard.md`.

## Planned Command

```powershell
python -m github_stars_dashboard run
```

## Development Commands

Run the collector in source-tree mode:

```powershell
$env:PYTHONPATH = "src"
python -m github_stars_dashboard.cli collect
```

Run the full pipeline dry-run:

```powershell
$env:PYTHONPATH = "src"
python -m github_stars_dashboard.cli run --dry-run
```

Generate a daily report from two saved snapshots:

```powershell
$env:PYTHONPATH = "src"
python -m github_stars_dashboard.cli report --start-date 2026-06-08 --end-date 2026-06-09
```

The report now enriches Top 10 repositories with GitHub README, recent release, and issue/PR signals. External web discovery is exposed as search links in the HTML report; automated third-party page reading will be added as a later integration point.

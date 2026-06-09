from github_stars_dashboard.config import load_config
from github_stars_dashboard.collect import _prepare_query


def test_load_config_defaults(tmp_path):
    config_file = tmp_path / "sources.yml"
    config_file.write_text("{}", encoding="utf-8")

    config = load_config(config_file)

    assert config.timezone == "Asia/Shanghai"
    assert config.top_n == 10
    assert config.candidate_limit == 1000


def test_prepare_query_adds_default_filters():
    query = _prepare_query(
        "stars:>100 pushed:>=2026-06-01",
        recent_date="2026-06-01",
        include_forks=False,
        include_archived=False,
    )

    assert query == "stars:>100 pushed:>=2026-06-01 fork:false archived:false"


def test_prepare_query_replaces_recent_date():
    query = _prepare_query(
        "stars:10..100 created:>=__RECENT_DATE__",
        recent_date="2026-06-01",
        include_forks=True,
        include_archived=True,
    )

    assert query == "stars:10..100 created:>=2026-06-01"

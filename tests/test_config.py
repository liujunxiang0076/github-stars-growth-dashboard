from github_stars_dashboard.config import load_config
from github_stars_dashboard.collect import _prepare_query
from github_stars_dashboard.growth import calculate_growth


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


def test_calculate_growth_ranks_by_delta():
    rows = calculate_growth(
        [
            {"full_name": "example/a", "html_url": "https://github.com/example/a", "stargazers_count": 10},
            {"full_name": "example/b", "html_url": "https://github.com/example/b", "stargazers_count": 100},
        ],
        [
            {"full_name": "example/a", "html_url": "https://github.com/example/a", "stargazers_count": 30},
            {"full_name": "example/b", "html_url": "https://github.com/example/b", "stargazers_count": 105},
        ],
        candidates=[
            {"full_name": "example/a", "language": "Python", "topics": ["cli"], "description": "A repo"},
            {"full_name": "example/b", "language": "Go", "topics": [], "description": "B repo"},
        ],
        top_n=2,
    )

    assert [row.full_name for row in rows] == ["example/a", "example/b"]
    assert rows[0].rank == 1
    assert rows[0].stars_delta == 20
    assert rows[0].growth_rate == 2

from github_stars_dashboard.config import load_config


def test_load_config_defaults(tmp_path):
    config_file = tmp_path / "sources.yml"
    config_file.write_text("{}", encoding="utf-8")

    config = load_config(config_file)

    assert config.timezone == "Asia/Shanghai"
    assert config.top_n == 10
    assert config.candidate_limit == 1000

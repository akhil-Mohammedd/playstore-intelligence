from pathlib import Path

from streamlit.testing.v1 import AppTest
from test_pipeline import fixture_frame


def _prepare_app(tmp_path, monkeypatch):
    data_dir = tmp_path / "synthetic_source"
    data_dir.mkdir()
    fixture_frame().to_csv(data_dir / "apps.csv", index=False)
    monkeypatch.setenv("PLAYSTORE_DATA_DIR", str(data_dir))
    return Path(__file__).resolve().parents[1] / "app.py"


def test_dashboard_smoke_without_crashing(tmp_path, monkeypatch):
    app = _prepare_app(tmp_path, monkeypatch)
    result = AppTest.from_file(str(app), default_timeout=60).run()
    assert not result.exception
    assert result.title[0].value == "Market Overview"


def test_navigation_filters_and_live_scoring_controls(tmp_path, monkeypatch):
    app = _prepare_app(tmp_path, monkeypatch)
    result = AppTest.from_file(str(app), default_timeout=90).run()
    assert not result.exception

    for page in [
        "Explore Categories",
        "Competition & Gaps",
        "Opportunity Finder",
        "Build Plan",
        "Market Overview",
    ]:
        result.session_state["research_page"] = page
        result.run()
        assert not result.exception, page

    result.session_state["research_page"] = "Explore Categories"
    result.run()
    result.multiselect(key="category_filter").set_value([]).run()
    assert not result.exception
    result.button(key="reset_category_filters").click().run()
    assert result.multiselect(key="category_filter").value
    result.checkbox(key="all_category_filter").set_value(True).run()
    assert not result.exception
    assert len(result.selectbox(key="profile_category").options) == 3

    result.session_state["research_page"] = "Opportunity Finder"
    result.run()
    baseline_scores = result.session_state["latest_ranked"]["score"].tolist()
    baseline_rank = result.session_state["latest_ranked"]["category"].head(5).tolist()
    result.slider(key="weight_demand").set_value(0.65).run()
    adjusted = result.session_state["latest_ranked"]
    assert baseline_scores != adjusted["score"].tolist()
    assert baseline_rank != adjusted["category"].head(5).tolist()
    result.button(key="reset_weights").click().run()
    assert result.session_state["weight_demand"] == 0.3
    assert not result.exception

from test_pipeline import fixture_frame

from playstore_intelligence.analytics import category_summary
from playstore_intelligence.cleaning import clean_apps
from playstore_intelligence.opportunity_scoring import (
    DEFAULT_WEIGHTS,
    explain_candidate,
    score_opportunities,
)
from playstore_intelligence.presentation import (
    build_plan_markdown,
    export_csv_bytes,
    filter_apps,
    gap_evidence,
    market_insights,
)
from playstore_intelligence.recommendations import recommendation_details


def test_filters_apply_search_type_rating_install_and_minimum_volume():
    apps = clean_apps(fixture_frame())[0]
    result = filter_apps(
        apps,
        categories=["TOOLS", "GAME"],
        app_type="Free",
        rating_status="Rated",
        min_install_lower_bound=100,
        query="Alpha",
    )
    assert result["app"].tolist() == ["Alpha"]
    assert filter_apps(apps, query="not-present").empty
    assert len(filter_apps(apps, min_apps=3)) == 0


def test_market_insights_and_gap_signals_are_data_derived():
    apps = clean_apps(fixture_frame())[0]
    summary = category_summary(apps)
    insights = market_insights(summary)
    assert insights
    assert all(
        "evidence" in insight and "limitation" in insight for insight in insights
    )
    gaps = gap_evidence(summary)
    assert "candidate_screening_signal" in gaps
    assert gaps["candidate_screening_signal"].between(0, 1).all()


def test_score_contribution_reconciles_and_missing_evidence_is_explicit():
    apps = clean_apps(fixture_frame())[0]
    summary = category_summary(apps)
    ranked = score_opportunities(summary)
    row = ranked.iloc[0]
    contributions = [row[f"{key}_contribution"] for key in DEFAULT_WEIGHTS]
    assert abs(sum(contributions) - row["score"]) < 1e-12
    assert abs(sum(float(row[f"{key}_weight"]) for key in DEFAULT_WEIGHTS) - 1) < 1e-12
    assert 0 <= float(row["score"]) <= 1
    assert row["feasibility_score"] == 0.5
    assert not bool(row["satisfaction_available"])
    assert row["satisfaction_score"] == 0.5
    assert "satisfaction" in explain_candidate(row)["missing"].lower()


def test_adjusted_weights_recompute_and_invalid_weights_fail():
    apps = clean_apps(fixture_frame())[0]
    summary = category_summary(apps)
    baseline = score_opportunities(summary)
    adjusted = score_opportunities(
        summary,
        {
            "demand": 0.0,
            "accessibility": 0.0,
            "satisfaction": 0.0,
            "gap": 0.0,
            "feasibility": 1.0,
        },
    )
    assert adjusted["score"].eq(0.5).all()
    assert not baseline["score"].equals(adjusted["score"])
    try:
        score_opportunities(summary, {key: 0.0 for key in DEFAULT_WEIGHTS})
    except ValueError:
        pass
    else:
        raise AssertionError("All-zero weights should be rejected")


def test_candidate_profile_and_markdown_export_include_hypothesis_and_evidence():
    apps = clean_apps(fixture_frame())[0]
    ranked = score_opportunities(category_summary(apps))
    profile = recommendation_details(ranked)[0]
    markdown = build_plan_markdown(profile)
    csv_data = export_csv_bytes(ranked.head(5))
    assert csv_data.startswith(b"category,")
    assert b"score" in csv_data
    assert "hypotheses" in markdown.lower()
    assert profile["evidence_summary"] in markdown
    assert "validation" in markdown.lower()

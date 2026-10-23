from pathlib import Path

import pandas as pd
import pytest

from playstore_intelligence.analytics import category_summary
from playstore_intelligence.cleaning import clean_apps, parse_installs, parse_size_mb
from playstore_intelligence.data_loader import (
    discover_csvs,
    find_app_csv,
    load_app_data,
)
from playstore_intelligence.opportunity_scoring import (
    DEFAULT_WEIGHTS,
    score_opportunities,
    sensitivity_analysis,
)


def fixture_frame():
    return pd.DataFrame(
        {
            "App": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"],
            "Category": ["TOOLS", "TOOLS", "GAME", "GAME", "EDUCATION", "EDUCATION"],
            "Rating": [4.5, None, 3.0, 6.0, 4.0, 4.2],
            "Reviews": ["1,200", "bad", "30", "3", "50", "60"],
            "Size": ["2 MB", "500kB", "Varies with device", "bad", "1 GB", "20 B"],
            "Installs": ["1,000+", "10+", "100+", "1,000,000+", "5,000+", "bad"],
            "Type": ["Free", "Free", "Paid", "Free", "Free", "Paid"],
            "Price": ["$0", "$0", "$1.99", "$0", "$0", "bad"],
            "Content Rating": ["Everyone"] * 6,
            "Genres": ["Tools", "Tools", "Arcade", "Arcade", "Education", "Education"],
            "Last Updated": [
                "January 1, 2018",
                "bad",
                "March 3, 2017",
                "May 2, 2018",
                "2018-01-01",
                "June 2, 2018",
            ],
        }
    )


def test_cleaning_preserves_bands_and_marks_invalid():
    clean, report = clean_apps(fixture_frame())
    assert clean.loc[0, "installs_raw"] == "1,000+"
    assert clean.loc[0, "estimated_installs_lower_bound"] == 1000
    assert pd.isna(clean.loc[3, "rating"])
    assert pd.isna(clean.loc[1, "reviews"])
    assert pd.isna(clean.loc[1, "last_updated"])
    assert report["cleaned_rows"] == 6


def test_parsers():
    assert parse_installs("1,000+") == 1000
    assert pd.isna(parse_installs("not known"))
    assert parse_size_mb("500kB") == pytest.approx(500 / 1024)
    assert parse_size_mb("1 GB") == 1024
    assert parse_size_mb("19M") == 19
    assert parse_size_mb("512k") == pytest.approx(512 / 1024)
    assert parse_size_mb(".5 MB") == pytest.approx(0.5)
    assert pd.isna(parse_size_mb("1..2 MB"))
    assert pd.isna(parse_size_mb("Varies with device"))


def test_category_summary_manual_and_empty():
    df, _ = clean_apps(fixture_frame())
    summary = category_summary(df)
    tools = summary.set_index("category").loc["TOOLS"]
    assert tools["app_count"] == 2
    assert tools["median_installs_lower_bound"] == 505
    assert tools["rated_apps"] == 1
    assert category_summary(df.iloc[0:0]).empty


def test_malformed_category_and_exact_duplicates_are_excluded_from_analysis():
    raw = fixture_frame()
    raw.loc[0, "Category"] = "1.9"
    raw = pd.concat([raw, raw.iloc[[1]]], ignore_index=True)
    clean, report = clean_apps(raw)
    assert report["invalid_category_rows"] == 1
    assert report["exact_duplicate_rows"] == 1
    assert report["analysis_eligible_rows"] == 5
    summary = category_summary(clean)
    assert "1.9" not in set(summary["category"])
    assert summary["app_count"].sum() == 5


def test_scoring_validates_weights_and_is_stable():
    summary = category_summary(clean_apps(fixture_frame())[0])
    ranked = score_opportunities(summary)
    assert len(ranked) == 3
    assert ranked.equals(score_opportunities(summary, DEFAULT_WEIGHTS))
    assert ranked["score"].between(0, 1).all()
    with pytest.raises(ValueError):
        score_opportunities(summary, {"demand": -1})
    assert not sensitivity_analysis(summary).empty


def test_loader_missing_malformed_and_discovery(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_app_data(tmp_path / "missing.csv")
    bad = tmp_path / "bad.csv"
    bad.write_text("wrong,columns\na,b\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        find_app_csv([bad])
    assert discover_csvs(tmp_path) == [bad]

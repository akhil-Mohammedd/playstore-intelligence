"""Descriptive market summaries; no causal interpretation is implied."""

from __future__ import annotations

import pandas as pd


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize category demand, competition, satisfaction and coverage."""
    if "analysis_eligible" in df.columns:
        df = df.loc[df["analysis_eligible"]].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "app_count",
                "total_estimated_installs_lower_bound",
                "median_installs_lower_bound",
                "mean_rating",
                "median_rating",
                "rating_coverage",
                "rated_apps",
                "median_reviews",
                "high_install_share",
                "free_share",
                "estimated_install_hhi",
            ]
        )
    result = (
        df.groupby("category", dropna=True)
        .agg(
            app_count=("app", "size"),
            total_estimated_installs_lower_bound=(
                "estimated_installs_lower_bound",
                "sum",
            ),
            median_installs_lower_bound=("estimated_installs_lower_bound", "median"),
            mean_rating=("rating", "mean"),
            median_rating=("rating", "median"),
            rated_apps=("rating", "count"),
            median_reviews=("reviews", "median"),
        )
        .reset_index()
    )
    result["rating_coverage"] = result["rated_apps"] / result["app_count"]
    result["high_install_share"] = (
        df.assign(high=df["estimated_installs_lower_bound"].ge(1_000_000))
        .groupby("category")["high"]
        .mean()
        .reindex(result["category"])
        .to_numpy()
    )
    result["free_share"] = (
        df.assign(free=df["type"].eq("Free"))
        .groupby("category")["free"]
        .mean()
        .reindex(result["category"])
        .to_numpy()
    )
    result["estimated_install_hhi"] = (
        df.groupby("category")
        .apply(_hhi, include_groups=False)
        .reindex(result["category"])
        .to_numpy()
    )
    return result.sort_values("category").reset_index(drop=True)


def _hhi(group: pd.DataFrame) -> float:
    values = group["estimated_installs_lower_bound"].dropna()
    total = values.sum()
    return float(((values / total) ** 2).sum()) if total > 0 else float("nan")


def overview(df: pd.DataFrame, quality: dict) -> dict:
    """Return calculated headline metrics for eligible records."""
    if "analysis_eligible" in df.columns:
        df = df.loc[df["analysis_eligible"]]
    return {
        "app_rows": len(df),
        "unique_app_names": int(df["app"].nunique()),
        "categories": int(df["category"].nunique()),
        "genres": int(df["genres"].nunique()),
        "rating_coverage": float(df["rating"].notna().mean()) if len(df) else 0.0,
        "free_share": float(df["type"].eq("Free").mean()) if len(df) else 0.0,
        "quality": quality,
    }

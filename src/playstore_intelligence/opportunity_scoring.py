"""Transparent heuristic category-level opportunity screening."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = {
    "demand": 0.30,
    "accessibility": 0.25,
    "satisfaction": 0.20,
    "gap": 0.15,
    "feasibility": 0.10,
}


def _scale(series: pd.Series, reverse: bool = False) -> pd.Series:
    values = series.astype(float)
    lo, hi = values.min(), values.max()
    if pd.isna(lo) or pd.isna(hi):
        return pd.Series(0.5, index=series.index)
    if hi == lo:
        return pd.Series(0.5, index=series.index)
    scaled = (values - lo) / (hi - lo)
    return 1 - scaled if reverse else scaled


def score_opportunities(
    summary: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
    min_rated_apps: int = 5,
) -> pd.DataFrame:
    """Rank categories as research starting points, not commercial forecasts."""
    weights = dict(weights or DEFAULT_WEIGHTS)
    if set(weights) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"Weights must contain exactly {sorted(DEFAULT_WEIGHTS)}")
    if (
        any(not np.isfinite(v) or v < 0 for v in weights.values())
        or sum(weights.values()) <= 0
    ):
        raise ValueError(
            "Weights must be finite, non-negative, and have a positive sum"
        )
    weights = {k: v / sum(weights.values()) for k, v in weights.items()}
    if summary.empty:
        return pd.DataFrame()
    frame = summary.copy()
    frame["demand"] = _scale(np.log1p(frame["median_installs_lower_bound"].fillna(0)))
    frame["accessibility"] = _scale(frame["app_count"], reverse=True)
    enough = frame["rated_apps"].ge(min_rated_apps)
    satisfaction = _scale(frame["mean_rating"].where(enough))
    frame["satisfaction"] = satisfaction.fillna(0.5)
    frame["gap"] = _scale(
        frame["estimated_install_hhi"].fillna(frame["estimated_install_hhi"].median()),
        reverse=True,
    )
    frame["feasibility"] = 0.5
    frame["score"] = sum(frame[key] * weights[key] for key in weights)
    frame["rating_evidence_sufficient"] = enough
    frame["confidence"] = np.where(
        enough & frame["app_count"].ge(10),
        "Moderate catalog evidence; low opportunity confidence",
        "Low catalog evidence; low opportunity confidence",
    )
    return frame.sort_values(
        ["score", "category"], ascending=[False, True]
    ).reset_index(drop=True)


def sensitivity_analysis(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare baseline ranking with equal-weight and demand-light alternatives."""
    scenarios = {
        "baseline": DEFAULT_WEIGHTS,
        "equal_weights": {key: 0.2 for key in DEFAULT_WEIGHTS},
        "demand_light": {
            "demand": 0.20,
            "accessibility": 0.30,
            "satisfaction": 0.25,
            "gap": 0.15,
            "feasibility": 0.10,
        },
    }
    outputs = []
    for name, weights in scenarios.items():
        ranked = score_opportunities(summary, weights)
        for rank, row in enumerate(ranked.head(5).itertuples(), start=1):
            outputs.append(
                {
                    "scenario": name,
                    "rank": rank,
                    "category": row.category,
                    "score": row.score,
                }
            )
    return pd.DataFrame(outputs)

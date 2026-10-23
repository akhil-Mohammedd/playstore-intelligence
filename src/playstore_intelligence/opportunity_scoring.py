"""Transparent, category-relative heuristic opportunity screening."""

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

COMPONENT_LABELS = {
    "demand": "Demand evidence",
    "accessibility": "Competitive accessibility",
    "satisfaction": "Observed user satisfaction",
    "gap": "Market-gap proxy",
    "feasibility": "MVP feasibility assumption",
}


def _scale(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Min-max scale available values, preserving missing values."""
    values = series.astype(float)
    lo, hi = values.min(), values.max()
    if pd.isna(lo) or pd.isna(hi):
        return pd.Series(np.nan, index=series.index, dtype=float)
    if hi == lo:
        scaled = pd.Series(0.5, index=series.index, dtype=float).where(values.notna())
    else:
        scaled = (values - lo) / (hi - lo)
    return 1 - scaled if reverse else scaled


def _validated_weights(weights: Mapping[str, float] | None) -> dict[str, float]:
    values = dict(weights or DEFAULT_WEIGHTS)
    if set(values) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"Weights must contain exactly {sorted(DEFAULT_WEIGHTS)}")
    if any(not np.isfinite(v) or v < 0 for v in values.values()):
        raise ValueError("Weights must be finite and non-negative")
    total = sum(values.values())
    if total <= 0:
        raise ValueError("At least one scoring weight must be greater than zero")
    return {key: value / total for key, value in values.items()}


def score_opportunities(
    summary: pd.DataFrame,
    weights: Mapping[str, float] | None = None,
    min_rated_apps: int = 5,
) -> pd.DataFrame:
    """Score categories from normalized data signals and explicit assumptions.

    Missing empirical components receive a neutral 0.5 score and are identified
    by availability flags. Feasibility is always a neutral, non-data-derived
    assumption. The final score is the weighted sum of component contributions.
    """
    active_weights = _validated_weights(weights)
    if summary.empty:
        return pd.DataFrame()
    frame = summary.copy()

    demand_metric = frame["median_installs_lower_bound"].where(
        frame["median_installs_lower_bound"].ge(0)
    )
    demand_available = demand_metric.notna()
    app_count = pd.to_numeric(frame["app_count"], errors="coerce")
    accessibility_available = app_count.gt(0)
    enough_ratings = (
        frame["rated_apps"].ge(min_rated_apps) & frame["mean_rating"].notna()
    )
    hhi_available = frame["estimated_install_hhi"].notna() & frame[
        "estimated_install_hhi"
    ].between(0, 1)

    frame["demand_metric"] = demand_metric
    frame["competition_app_count"] = app_count
    frame["satisfaction_metric"] = frame["mean_rating"].where(enough_ratings)
    frame["market_gap_hhi"] = frame["estimated_install_hhi"].where(hhi_available)
    frame["demand_available"] = demand_available
    frame["accessibility_available"] = accessibility_available
    frame["satisfaction_available"] = enough_ratings
    frame["gap_available"] = hhi_available
    frame["rating_evidence_sufficient"] = enough_ratings

    components = {
        "demand": _scale(np.log1p(demand_metric)),
        "accessibility": _scale(app_count, reverse=True).where(accessibility_available),
        "satisfaction": _scale(frame["mean_rating"].where(enough_ratings)),
        "gap": _scale(frame["estimated_install_hhi"], reverse=True).where(
            hhi_available
        ),
        "feasibility": pd.Series(0.5, index=frame.index, dtype=float),
    }
    available = {
        "demand": demand_available,
        "accessibility": accessibility_available,
        "satisfaction": enough_ratings,
        "gap": hhi_available,
        "feasibility": pd.Series(False, index=frame.index),
    }
    contribution_columns = []
    for name, values in components.items():
        frame[f"{name}_score"] = values.fillna(0.5)
        frame[f"{name}_weight"] = active_weights[name]
        frame[f"{name}_contribution"] = frame[f"{name}_score"] * active_weights[name]
        frame[f"{name}_available"] = available[name]
        contribution_columns.append(f"{name}_contribution")

    frame["score"] = frame[contribution_columns].sum(axis=1).clip(0, 1)
    empirical_weights = sum(
        active_weights[name]
        for name in ("demand", "accessibility", "satisfaction", "gap")
    )
    if empirical_weights > 0:
        frame["evidence_coverage"] = (
            sum(
                frame[f"{name}_available"].astype(float) * active_weights[name]
                for name in ("demand", "accessibility", "satisfaction", "gap")
            )
            / empirical_weights
        )
    else:
        frame["evidence_coverage"] = 0.0
    frame["missing_components"] = frame.apply(
        lambda row: (
            ", ".join(
                COMPONENT_LABELS[name]
                for name in ("demand", "accessibility", "satisfaction", "gap")
                if not bool(row[f"{name}_available"])
            )
            or "None"
        ),
        axis=1,
    )
    frame["confidence"] = np.where(
        enough_ratings & app_count.ge(10),
        "Moderate catalog evidence; low opportunity confidence",
        "Low catalog evidence; low opportunity confidence",
    )
    frame["weights_normalized"] = str(
        {key: round(value, 4) for key, value in active_weights.items()}
    )
    return frame.sort_values(
        ["score", "category"], ascending=[False, True]
    ).reset_index(drop=True)


def explain_candidate(
    candidate: pd.Series | Mapping, weights: Mapping[str, float] | None = None
) -> dict[str, str]:
    """Build a metric-grounded explanation from one scored candidate row."""
    active_weights = _validated_weights(weights)
    row = candidate
    components = [name for name in DEFAULT_WEIGHTS if bool(row[f"{name}_available"])]
    contributions = {name: float(row[f"{name}_contribution"]) for name in components}
    strongest = max(contributions, key=contributions.get) if contributions else None
    weakest = min(contributions, key=contributions.get) if contributions else None
    median_installs = row.get("demand_metric", float("nan"))
    mean_rating = row.get("satisfaction_metric", float("nan"))
    hhi = row.get("market_gap_hhi", float("nan"))
    app_count = int(row.get("competition_app_count", 0))
    rated_apps = int(row.get("rated_apps", 0))
    evidence = (
        f"{app_count:,} eligible app records; median install-band lower bound "
        f"{median_installs:,.0f}"
        if pd.notna(median_installs)
        else f"{app_count:,} eligible app records; median install evidence unavailable"
    )
    evidence += (
        f"; mean rating {mean_rating:.2f} from {rated_apps:,} rated apps"
        if pd.notna(mean_rating)
        else f"; rating evidence withheld (fewer than 5 rated apps; {rated_apps:,} available)"
    )
    evidence += (
        f"; lower-bound concentration HHI {hhi:.3f}"
        if pd.notna(hhi)
        else "; concentration evidence unavailable"
    )
    strongest_text = (
        f"{COMPONENT_LABELS[strongest]} contributes {contributions[strongest]:.3f} "
        f"({float(row[f'{strongest}_score']):.2f} component × {active_weights[strongest]:.0%} active weight)."
        if strongest
        else "No empirical component is available."
    )
    weakest_text = (
        f"{COMPONENT_LABELS[weakest]} contributes {contributions[weakest]:.3f} "
        f"({float(row[f'{weakest}_score']):.2f} component × {active_weights[weakest]:.0%} active weight)."
        if weakest
        else "No empirical component is available."
    )
    missing = str(row.get("missing_components", "None"))
    accessibility = float(row.get("accessibility_score", 0.5))
    competition_concern = (
        f"{app_count:,} eligible listings; competitive-accessibility subscore "
        f"{accessibility:.2f}/1.00 (higher means fewer listings in this candidate set). "
        "Listing counts do not measure competitor quality or market entry barriers."
    )
    return {
        "evidence": evidence + ".",
        "strongest": strongest_text,
        "weakest": weakest_text,
        "competition_concern": competition_concern,
        "missing": missing,
        "confidence": str(row["confidence"]),
    }


def sensitivity_analysis(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare rankings under three reasonable, deterministic weight sets."""
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
    baseline = score_opportunities(summary, scenarios["baseline"])
    baseline_ranks = {
        row.category: rank for rank, row in enumerate(baseline.itertuples(), start=1)
    }
    for name, scenario_weights in scenarios.items():
        ranked = score_opportunities(summary, scenario_weights)
        for rank, row in enumerate(ranked.head(5).itertuples(), start=1):
            outputs.append(
                {
                    "scenario": name,
                    "rank": rank,
                    "category": row.category,
                    "score": row.score,
                    "baseline_rank": baseline_ranks.get(row.category),
                    "rank_change": baseline_ranks.get(row.category, rank) - rank,
                    "score_change": row.score
                    - float(
                        baseline.loc[
                            baseline["category"].eq(row.category), "score"
                        ].iloc[0]
                    ),
                }
            )
    return pd.DataFrame(outputs)

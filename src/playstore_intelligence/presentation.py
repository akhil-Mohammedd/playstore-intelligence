"""Reusable, data-backed presentation and planning helpers."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


def filter_apps(
    df: pd.DataFrame,
    categories: Iterable[str] | None = None,
    app_type: str = "All",
    min_apps: int = 0,
    rating_status: str = "All",
    min_install_lower_bound: float = 0,
    query: str = "",
) -> pd.DataFrame:
    """Apply category-explorer filters consistently to an eligible app frame."""
    result = df.copy()
    if categories is not None:
        result = result[result["category"].isin(list(categories))]
    if app_type != "All":
        result = result[result["type"].eq(app_type)]
    if rating_status == "Rated":
        result = result[result["rating"].notna()]
    elif rating_status == "Missing rating":
        result = result[result["rating"].isna()]
    if min_install_lower_bound > 0:
        result = result[
            result["estimated_installs_lower_bound"].ge(min_install_lower_bound)
        ]
    if query.strip():
        result = result[
            result["app"].str.contains(query.strip(), case=False, na=False, regex=False)
        ]
    if min_apps:
        counts = result["category"].value_counts()
        keep = counts[counts.ge(min_apps)].index
        result = result[result["category"].isin(keep)]
    return result


def market_insights(summary: pd.DataFrame) -> list[dict[str, str]]:
    """Generate concise descriptive observations from observed category metrics."""
    if summary.empty:
        return []
    insights: list[dict[str, str]] = []
    demand = summary.dropna(subset=["median_installs_lower_bound"])
    if not demand.empty:
        leader = demand.sort_values(
            ["median_installs_lower_bound", "app_count"], ascending=[False, False]
        ).iloc[0]
        overall = demand["median_installs_lower_bound"].median()
        ratio = leader["median_installs_lower_bound"] / overall if overall else np.nan
        insights.append(
            {
                "title": f"{leader['category']} has the largest median install-band lower bound",
                "evidence": f"{leader['median_installs_lower_bound']:,.0f} lower-bound installs per app (n={int(leader['app_count'])}); overall category median is {overall:,.0f}.",
                "meaning": f"The category's median is {ratio:.1f}× the cross-category median."
                if pd.notna(ratio)
                else "The overall comparison median is unavailable.",
                "limitation": "Bands are coarse lower bounds from a historical snapshot, not exact installs or current demand.",
            }
        )
    rated = summary[summary["rated_apps"].ge(5)].dropna(subset=["mean_rating"])
    if not rated.empty:
        leader = rated.sort_values("mean_rating", ascending=False).iloc[0]
        insights.append(
            {
                "title": f"{leader['category']} leads mean rating among sufficiently rated categories",
                "evidence": f"Mean rating {leader['mean_rating']:.2f}/5 from {int(leader['rated_apps']):,} rated apps; rating coverage {leader['rating_coverage']:.1%}.",
                "meaning": "This is an observed listing-rating summary, not a measure of retention or willingness to pay.",
                "limitation": "Ratings are selective and do not identify which features users value or what they find missing.",
            }
        )
    if summary["estimated_install_hhi"].notna().any():
        leader = summary.loc[summary["estimated_install_hhi"].idxmax()]
        insights.append(
            {
                "title": f"{leader['category']} has the highest estimated-install concentration",
                "evidence": f"Approximate HHI {leader['estimated_install_hhi']:.3f} across {int(leader['app_count'])} eligible records.",
                "meaning": "The parsed install lower bounds are more concentrated among listings in this category.",
                "limitation": "Install bands make concentration approximate; this does not establish barriers, market share, or a defensible gap.",
            }
        )
    return insights


def gap_evidence(summary: pd.DataFrame) -> pd.DataFrame:
    """Compare observed demand, app counts, satisfaction and concentration."""
    if summary.empty:
        return pd.DataFrame()
    result = summary.copy()
    install_median = result["median_installs_lower_bound"].median()
    app_median = result["app_count"].median()
    result["demand_relative_to_overall_median"] = (
        result["median_installs_lower_bound"] / install_median
        if pd.notna(install_median) and install_median > 0
        else np.nan
    )
    result["app_count_relative_to_median"] = (
        result["app_count"] / app_median
        if pd.notna(app_median) and app_median > 0
        else np.nan
    )
    # A two-signal screening index, explicitly not a measured unmet-need metric.
    demand_rank = result["median_installs_lower_bound"].rank(pct=True)
    accessibility_rank = result["app_count"].rank(pct=True, ascending=False)
    result["candidate_screening_signal"] = (demand_rank * accessibility_rank).pow(0.5)
    return result.sort_values(
        "candidate_screening_signal", ascending=False
    ).reset_index(drop=True)


def export_csv_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize the currently filtered/ranked view for Streamlit downloads."""
    return frame.to_csv(index=False).encode("utf-8")


def build_plan_markdown(profile: dict) -> str:
    """Create an exportable hypothesis-led MVP and validation plan."""
    mvp = profile.get("mvp_features", [])
    postpone = profile.get("postpone", [])
    validation = profile.get("validation", [])
    risks = profile.get("risks", [])
    return f"""# MVP research plan: {profile["concept"]}

> Product and audience statements below are hypotheses for validation, not facts inferred from catalog metrics.

## Problem and audience
- **Audience hypothesis:** {profile["target_audience"]}
- **Problem hypothesis:** {profile["problem_hypothesis"]}
- **Proposed value proposition:** Help the target user complete one clearly scoped task more easily. Validate this wording in interviews before building.
- **Evidence category:** {profile["category"]}
- **Dataset evidence:** {profile["evidence_summary"]}
- **Opportunity score:** {profile["weighted_score"]:.3f} heuristic; not a success probability.

## MVP scope
{_bullets(mvp)}

### Postpone
{_bullets(postpone)}

## Suggested implementation milestones
1. Interview target users and document the repeated workflow/pain point.
2. Prototype the single core workflow; test comprehension and task completion.
3. Implement the narrow Android MVP and instrument only consented, necessary product events.
4. Run a small opt-in pilot; review task completion, repeat use, qualitative feedback, and crashes.
5. Decide to iterate, narrow, or stop using pre-agreed validation criteria.

## Technical starting point (engineering suggestion, not dataset evidence)
- Kotlin + Jetpack Compose for a native Android prototype.
- Keep the first release local/offline if the use case permits; add persistence only for demonstrated workflow needs.
- Defer accounts, cloud sync, paid acquisition, and third-party integrations until user validation establishes a need.

## Validation experiments
{_bullets(validation)}

## Success measures to define before testing
- Target-user interview evidence for a repeated problem.
- Prototype task completion and observed points of confusion.
- Opt-in pilot engagement and qualitative usefulness feedback.
- Reliability and crash-free sessions during the pilot.

## Risks and evidence gaps
{_bullets(risks)}

No revenue, acquisition, market-size, or commercial-success estimate is supported by this dataset.
"""


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None specified."

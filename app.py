"""Explainable Google Play Store market research dashboard."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from playstore_intelligence.analytics import category_summary, overview
from playstore_intelligence.cleaning import clean_apps, parse_installs
from playstore_intelligence.data_loader import (
    discover_csvs,
    download_public_dataset,
    find_app_csv,
    find_dataset_dir,
    load_app_data,
)
from playstore_intelligence.opportunity_scoring import (
    COMPONENT_LABELS,
    DEFAULT_WEIGHTS,
    explain_candidate,
    score_opportunities,
    sensitivity_analysis,
)
from playstore_intelligence.presentation import (
    build_plan_markdown,
    export_csv_bytes,
    filter_apps,
    gap_evidence,
    market_insights,
)
from playstore_intelligence.recommendations import recommendation_details

st.set_page_config(
    page_title="PlayStore Intelligence",
    page_icon="PI",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    "Market Overview",
    "Explore Categories",
    "Competition & Gaps",
    "Opportunity Finder",
    "Build Plan",
]
ACCENT = "#176B87"


@st.cache_data(show_spinner="Loading and validating the catalog…")
def get_data(configured_dir: str | None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load a configured local folder, data/raw, or the KaggleHub cache."""
    local = ROOT / "data" / "raw"
    explicit_dir = Path(configured_dir) if configured_dir else None
    if explicit_dir is None and local.exists() and list(local.rglob("*.csv")):
        explicit_dir = local
    try:
        source_dir = find_dataset_dir(explicit_dir)
    except FileNotFoundError:
        if explicit_dir is not None:
            raise
        source_dir = download_public_dataset()
    raw = load_app_data(find_app_csv(discover_csvs(source_dir)))
    return clean_apps(raw)


@st.cache_data(show_spinner=False)
def get_category_summary(frame: pd.DataFrame) -> pd.DataFrame:
    return category_summary(frame)


def style_chart(fig: go.Figure, height: int = 360) -> go.Figure:
    """Apply a consistent quiet chart style without DOM-dependent CSS."""
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 12, "r": 12, "t": 58, "b": 12},
        font={"family": "Arial, sans-serif", "color": "#263746", "size": 12},
        title={"x": 0.02, "xanchor": "left", "font": {"size": 16}},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E8EDF0", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def show_empty(message: str) -> None:
    st.info(message)
    st.caption("Try clearing a filter or selecting a broader category set.")


def format_band(value: float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B+"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M+"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K+"
    return f"{value:,.0f}+"


def display_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """Select and label only the comparison fields users need."""
    if summary.empty:
        return summary
    table = summary[
        [
            "category",
            "app_count",
            "median_installs_lower_bound",
            "mean_rating",
            "rating_coverage",
            "median_reviews",
            "estimated_install_hhi",
            "free_share",
        ]
    ].rename(
        columns={
            "category": "Category",
            "app_count": "Eligible apps",
            "median_installs_lower_bound": "Median install-band lower bound / app",
            "mean_rating": "Mean rating / 5",
            "rating_coverage": "Rating coverage",
            "median_reviews": "Median reviews",
            "estimated_install_hhi": "Approx. install concentration (HHI)",
            "free_share": "Free share",
        }
    )
    return table


def show_market_overview(data: pd.DataFrame, quality: dict[str, Any]) -> None:
    st.title("Market Overview")
    st.caption(
        "Start with the historical catalog evidence. Install values are band lower bounds—not exact downloads or current-market measurements."
    )
    summary = get_category_summary(data)
    metrics = overview(data, quality)
    rating_sample_categories = (
        int((summary["rated_apps"] >= 5).sum()) if not summary.empty else 0
    )

    kpis = st.columns(4)
    kpis[0].metric("Eligible app records", f"{metrics['app_rows']:,}")
    kpis[1].metric("Categories represented", f"{metrics['categories']:,}")
    kpis[2].metric("Valid rating coverage", f"{metrics['rating_coverage']:.1%}")
    kpis[3].metric("Categories with ≥5 ratings", f"{rating_sample_categories:,}")

    st.subheader("Market snapshot")
    left, right = st.columns(2)
    with left:
        top_categories = summary.nlargest(10, "app_count").sort_values("app_count")
        fig = px.bar(
            top_categories,
            x="app_count",
            y="category",
            orientation="h",
            color_discrete_sequence=[ACCENT],
            labels={"app_count": "Eligible app records", "category": "Category"},
            title="Where are listings concentrated? · 10 largest categories",
            hover_data={"app_count": ":,", "category": True},
        )
        st.plotly_chart(style_chart(fig, 390), width="stretch")
    with right:
        bands = (
            data["installs_raw"]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .rename_axis("Install band (source text)")
            .reset_index(name="Listings")
        )
        bands["_order"] = bands["Install band (source text)"].map(parse_installs)
        bands = bands.sort_values("_order", na_position="last")
        fig = px.bar(
            bands,
            x="Install band (source text)",
            y="Listings",
            color_discrete_sequence=["#6A9E9A"],
            labels={
                "Listings": "Eligible app records",
                "Install band (source text)": "Original install band",
            },
            title="How listings are distributed across source install bands",
            hover_data={"Listings": ":,", "_order": False},
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(style_chart(fig, 390), width="stretch")

    insight_list = market_insights(summary)
    st.subheader("What the data tells us")
    st.caption(
        "Descriptive comparisons only. Each observation includes its denominator and an interpretation limit."
    )
    if not insight_list:
        show_empty(
            "There are not enough valid category metrics to generate a market observation."
        )
    else:
        for start in range(0, len(insight_list), 2):
            pair = st.columns(2)
            for col, insight in zip(pair, insight_list[start : start + 2]):
                with col, st.container(border=True):
                    st.markdown(f"**{insight['title']}**")
                    st.write(insight["evidence"])
                    st.caption(insight["meaning"])
                    st.caption(f"Limit: {insight['limitation']}")

    with st.expander("Ratings, pricing and review distributions"):
        tab_rating, tab_business = st.tabs(["Ratings & reviews", "Free & paid"])
        with tab_rating:
            chart_left, chart_right = st.columns(2)
            with chart_left:
                fig = px.histogram(
                    data.dropna(subset=["rating"]),
                    x="rating",
                    nbins=20,
                    labels={
                        "rating": "Observed rating (1–5)",
                        "count": "Eligible listings",
                    },
                    title="Observed rating distribution",
                    color_discrete_sequence=[ACCENT],
                )
                st.plotly_chart(style_chart(fig, 330), width="stretch")
            with chart_right:
                review_data = data[data["reviews"].ge(0)].copy()
                review_data["log_reviews"] = (review_data["reviews"] + 1).map(
                    math.log10
                )
                fig = px.histogram(
                    review_data,
                    x="log_reviews",
                    nbins=30,
                    labels={
                        "log_reviews": "log₁₀(review count + 1)",
                        "count": "Eligible listings",
                    },
                    title="Review-count distribution · log scale",
                    color_discrete_sequence=["#6A9E9A"],
                )
                st.plotly_chart(style_chart(fig, 330), width="stretch")
                st.caption(
                    "Review counts are strongly skewed; the x-axis uses log₁₀(count + 1)."
                )
        with tab_business:
            free_paid = (
                data["type"]
                .fillna("Unknown")
                .value_counts()
                .rename_axis("Listing type")
                .reset_index(name="Apps")
            )
            fig = px.bar(
                free_paid,
                x="Listing type",
                y="Apps",
                color="Listing type",
                color_discrete_map={
                    "Free": ACCENT,
                    "Paid": "#D49A3A",
                    "Unknown": "#9AA6AD",
                },
                title="Free and paid listings in eligible records",
                labels={"Apps": "Eligible app records"},
            )
            st.plotly_chart(style_chart(fig, 330), width="stretch")
            st.caption(
                "This compares listing types; it says nothing about revenue, conversion, or profitability."
            )

    excluded = quality["raw_rows"] - quality["analysis_eligible_rows"]
    st.caption(
        f"Data quality: {excluded:,} source rows excluded from category analysis; repeated names are retained unless full rows are exact duplicates. Detailed quality counts and cleaning rules follow below."
    )


def show_category_explorer(data: pd.DataFrame) -> None:
    st.title("Explore Categories")
    st.caption(
        "Filter eligible app records, compare category profiles, and inspect the app-level records behind the summaries."
    )
    categories = sorted(data["category"].dropna().unique().tolist())
    default_categories = (
        data["category"].value_counts().head(5).index.tolist() if categories else []
    )

    def reset_category_filters() -> None:
        st.session_state["category_filter"] = default_categories
        st.session_state["all_category_filter"] = False
        st.session_state["type_filter"] = "All"
        st.session_state["rating_filter"] = "All"
        st.session_state["minimum_apps"] = 0
        st.session_state["minimum_installs"] = 0
        st.session_state["category_search"] = ""

    with st.container(border=True):
        st.button(
            "Reset filters",
            key="reset_category_filters",
            on_click=reset_category_filters,
        )
        c1, c2, c3 = st.columns([1.3, 1, 1])
        all_categories = c1.checkbox("All categories", key="all_category_filter")
        chosen_categories = c1.multiselect(
            "Selected categories",
            categories,
            default=default_categories,
            key="category_filter",
            disabled=all_categories,
        )
        selected = categories if all_categories else chosen_categories
        app_type = c2.selectbox(
            "Listing type", ["All", "Free", "Paid"], key="type_filter"
        )
        rating_status = c3.selectbox(
            "Rating data", ["All", "Rated", "Missing rating"], key="rating_filter"
        )
        c4, c5, c6 = st.columns([1, 1, 1.4])
        min_apps = c4.number_input(
            "Minimum apps per category",
            min_value=0,
            max_value=1000,
            value=0,
            step=1,
            key="minimum_apps",
        )
        min_installs = c5.selectbox(
            "Minimum install-band lower bound",
            [0, 10, 100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000],
            format_func=lambda value: "Any" if value == 0 else format_band(value),
            key="minimum_installs",
        )
        query = c6.text_input("App name contains", key="category_search")

    filtered = filter_apps(
        data,
        categories=selected,
        app_type=app_type,
        min_apps=int(min_apps),
        rating_status=rating_status,
        min_install_lower_bound=float(min_installs),
        query=query,
    )
    if filtered.empty:
        show_empty("No eligible apps match the current filters.")
        return

    filtered_summary = get_category_summary(filtered)
    kpis = st.columns(3)
    kpis[0].metric("Matching app records", f"{len(filtered):,}")
    kpis[1].metric("Categories in result", f"{filtered['category'].nunique():,}")
    kpis[2].metric("Rating coverage", f"{filtered['rating'].notna().mean():.1%}")

    sort_label = st.selectbox(
        "Sort category comparison by",
        [
            "Median installs / app",
            "Eligible apps",
            "Mean rating",
            "Rating coverage",
            "Median reviews",
        ],
        key="category_sort",
    )
    sort_key = {
        "Median installs / app": "median_installs_lower_bound",
        "Eligible apps": "app_count",
        "Mean rating": "mean_rating",
        "Rating coverage": "rating_coverage",
        "Median reviews": "median_reviews",
    }[sort_label]
    st.dataframe(
        display_summary(filtered_summary).sort_values(
            {
                "median_installs_lower_bound": "Median install-band lower bound / app",
                "app_count": "Eligible apps",
                "mean_rating": "Mean rating / 5",
                "rating_coverage": "Rating coverage",
                "median_reviews": "Median reviews",
            }[sort_key],
            ascending=False,
            na_position="last",
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Median install-band lower bound / app": st.column_config.NumberColumn(
                format="localized"
            ),
            "Mean rating / 5": st.column_config.NumberColumn(format="%.2f"),
            "Rating coverage": st.column_config.NumberColumn(format="percent"),
            "Free share": st.column_config.NumberColumn(format="percent"),
            "Approx. install concentration (HHI)": st.column_config.NumberColumn(
                format="%.3f"
            ),
        },
    )
    st.download_button(
        "Export matching app records",
        export_csv_bytes(filtered),
        file_name="filtered_play_store_apps.csv",
        mime="text/csv",
        key="export_category_apps",
    )

    selected_profile = st.selectbox(
        "Category profile",
        filtered_summary["category"].tolist(),
        key="profile_category",
    )
    category_data = filtered[filtered["category"].eq(selected_profile)]
    profile = filtered_summary[filtered_summary["category"].eq(selected_profile)].iloc[
        0
    ]
    st.subheader(f"{selected_profile.replace('_', ' ').title()} profile")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Eligible apps", f"{int(profile['app_count']):,}")
    p2.metric(
        "Median install-band lower bound / app",
        format_band(float(profile["median_installs_lower_bound"]))
        if pd.notna(profile["median_installs_lower_bound"])
        else "Not available",
    )
    p3.metric(
        "Mean rating",
        f"{profile['mean_rating']:.2f}/5"
        if pd.notna(profile["mean_rating"])
        else "Not available",
    )
    p4.metric(
        "Free listings",
        f"{profile['free_share']:.1%}"
        if pd.notna(profile["free_share"])
        else "Not available",
    )
    left, right = st.columns(2)
    with left:
        dist = (
            category_data["installs_raw"]
            .fillna("Missing")
            .astype(str)
            .value_counts()
            .rename_axis("Source install band")
            .reset_index(name="Apps")
        )
        dist["_order"] = dist["Source install band"].map(parse_installs)
        dist = dist.sort_values("_order", na_position="last")
        fig = px.bar(
            dist,
            x="Source install band",
            y="Apps",
            title="Observed source install bands",
            color_discrete_sequence=[ACCENT],
            labels={"Apps": "Eligible app records"},
        )
        fig.update_xaxes(tickangle=-35)
        st.plotly_chart(style_chart(fig, 330), width="stretch")
    with right:
        rated = category_data.dropna(subset=["rating"])
        if rated.empty:
            show_empty("No ratings are available for this filtered category.")
        else:
            fig = px.histogram(
                rated,
                x="rating",
                nbins=15,
                title="Observed ratings in selected category",
                color_discrete_sequence=["#6A9E9A"],
                labels={"rating": "Rating (1–5)", "count": "Eligible listings"},
            )
            st.plotly_chart(style_chart(fig, 330), width="stretch")
    st.caption(
        "Profile metrics and plots reflect all active filters. Install values remain source bands/lower bounds, not exact totals."
    )
    show_apps = st.toggle(
        "Show matching app records", value=False, key="show_category_apps"
    )
    if show_apps:
        st.dataframe(
            category_data[
                [
                    "app",
                    "category",
                    "rating",
                    "reviews",
                    "installs_raw",
                    "estimated_installs_lower_bound",
                    "type",
                    "price_usd",
                    "size_mb",
                    "last_updated",
                ]
            ].head(250),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Showing at most 250 of {len(category_data):,} matching rows; export includes the complete filtered set."
        )


def show_competition(data: pd.DataFrame, summary: pd.DataFrame) -> None:
    st.title("Competition & Gaps")
    st.caption(
        "Screen for evidence worth investigating. These proxies do not prove unmet demand or absence of competitors."
    )
    with st.container(border=True):
        st.markdown("**How to read this page**")
        st.write(
            "Demand proxy = category median install-band lower bound per eligible app. Competition proxy = eligible app count and concentration of those lower bounds. Lower concentration or fewer apps may improve accessibility, but neither proves an underserved niche."
        )
    if summary.empty:
        show_empty("No eligible categories are available for comparison.")
        return

    comparison = gap_evidence(summary)
    left, right = st.columns([1.5, 1])
    with left:
        fig = px.scatter(
            summary,
            x="app_count",
            y="median_installs_lower_bound",
            color="estimated_install_hhi",
            size="rating_coverage",
            hover_name="category",
            hover_data={
                "app_count": ":,",
                "median_installs_lower_bound": ":,.0f",
                "mean_rating": ":.2f",
                "rating_coverage": ":.1%",
                "estimated_install_hhi": ":.3f",
            },
            labels={
                "app_count": "Eligible listings (competition volume)",
                "median_installs_lower_bound": "Median install-band lower bound / app",
                "estimated_install_hhi": "Approx. HHI",
                "rating_coverage": "Rating coverage",
            },
            title="Observed demand proxy versus listing volume",
            log_y=True,
            color_continuous_scale=["#DCE8EB", ACCENT, "#284C63"],
        )
        st.plotly_chart(style_chart(fig, 430), width="stretch")
        st.caption(
            "Each point is a category. Y is logarithmic because install-band lower bounds are highly skewed. Point size represents rating coverage."
        )
    with right:
        st.markdown("**Candidate screening signals**")
        st.write(
            "The index is the geometric mean of demand percentile and inverse app-count percentile. It is a triage aid only—not a measured market gap and not the opportunity score."
        )
        table = comparison.head(8)[
            [
                "category",
                "app_count",
                "median_installs_lower_bound",
                "estimated_install_hhi",
                "candidate_screening_signal",
            ]
        ].rename(
            columns={
                "category": "Category",
                "app_count": "Apps",
                "median_installs_lower_bound": "Median install lower bound",
                "estimated_install_hhi": "Approx. HHI",
                "candidate_screening_signal": "Screening signal",
            }
        )
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "Median install lower bound": st.column_config.NumberColumn(
                    format="localized"
                ),
                "Approx. HHI": st.column_config.NumberColumn(format="%.3f"),
                "Screening signal": st.column_config.NumberColumn(format="%.2f"),
            },
        )

    categories = comparison["category"].tolist()
    selected = st.selectbox(
        "Inspect a category's evidence", categories, key="competition_category"
    )
    row = summary[summary["category"].eq(selected)].iloc[0]
    median_all = summary["median_installs_lower_bound"].median()
    median_apps = summary["app_count"].median()
    a, b, c, d = st.columns(4)
    a.metric(
        "Eligible app records",
        f"{int(row['app_count']):,}",
        delta=f"{row['app_count'] / median_apps:.2f}× category median"
        if median_apps
        else None,
        delta_color="off",
    )
    b.metric(
        "Median install lower bound / app",
        format_band(row["median_installs_lower_bound"])
        if pd.notna(row["median_installs_lower_bound"])
        else "Unavailable",
        delta=f"{row['median_installs_lower_bound'] / median_all:.2f}× category median"
        if median_all
        else None,
        delta_color="off",
    )
    c.metric(
        "Rating evidence",
        f"{row['mean_rating']:.2f}/5"
        if pd.notna(row["mean_rating"])
        else "Unavailable",
        help=f"{int(row['rated_apps']):,} rated listings; coverage {row['rating_coverage']:.1%}",
    )
    d.metric(
        "Approx. install HHI",
        f"{row['estimated_install_hhi']:.3f}"
        if pd.notna(row["estimated_install_hhi"])
        else "Unavailable",
    )
    st.markdown("**Evidence interpretation**")
    st.write(
        f"{selected} contains {int(row['app_count']):,} eligible catalog records. Its median per-app install-band lower bound is {row['median_installs_lower_bound']:,.0f} versus {median_all:,.0f} across categories; approximate concentration is {row['estimated_install_hhi']:.3f}. These comparisons can prioritize further research, but cannot establish unmet need, competitor weakness, current demand, or commercial viability."
    )
    st.info(
        "Next research: inspect representative apps and their recent reviews, interview target users about a specific workflow, and compare alternatives before treating this as a product gap."
    )


def _weight_controls() -> dict[str, float]:
    st.subheader("Scoring configuration")
    if st.button("Reset to documented defaults", key="reset_weights"):
        for name, value in DEFAULT_WEIGHTS.items():
            st.session_state[f"weight_{name}"] = float(value)
        st.rerun()
    weights_help = {
        "demand": "Min-max normalized log median install-band lower bound per app; band values are not exact installs.",
        "accessibility": "Inverse min-max eligible app count; fewer listings yields a higher score.",
        "satisfaction": "Min-max category mean rating, available only with at least five rated listings.",
        "gap": "Inverse min-max HHI calculated from install-band lower bounds; proxy only, not proof of unmet need.",
        "feasibility": "Fixed neutral 0.5 engineering assumption; not calculated from catalog data.",
    }
    weights: dict[str, float] = {}
    columns = st.columns(2)
    for index, (name, default) in enumerate(DEFAULT_WEIGHTS.items()):
        key = f"weight_{name}"
        st.session_state.setdefault(key, float(default))
        weights[name] = columns[index % 2].slider(
            f"{COMPONENT_LABELS[name]} weight",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key=key,
            help=weights_help[name],
        )
    total = sum(weights.values())
    if total <= 0:
        st.error(
            "Set at least one weight above zero. The scores cannot be calculated with all-zero weights."
        )
        return {}
    normalized = {key: value / total for key, value in weights.items()}
    st.caption(
        f"Active raw weights sum to {total:.2f}; scores use normalized weights that sum to 100%."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Factor": COMPONENT_LABELS[k],
                    "Entered weight": weights[k],
                    "Applied normalized weight": normalized[k],
                    "Definition": weights_help[k],
                }
                for k in weights
            ]
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Entered weight": st.column_config.NumberColumn(format="percent"),
            "Applied normalized weight": st.column_config.NumberColumn(
                format="percent"
            ),
        },
    )
    return weights


def _component_table(candidate: pd.Series, weights: dict[str, float]) -> pd.DataFrame:
    metrics = {
        "demand": f"Median install lower bound: {candidate['demand_metric']:,.0f}"
        if pd.notna(candidate["demand_metric"])
        else "Missing; neutral fallback",
        "accessibility": f"Eligible app listings: {int(candidate['competition_app_count']):,}"
        if bool(candidate["accessibility_available"])
        else "Missing; neutral fallback",
        "satisfaction": f"Mean rating: {candidate['satisfaction_metric']:.2f}/5 from {int(candidate['rated_apps']):,}"
        if bool(candidate["satisfaction_available"])
        else f"Insufficient rating sample ({int(candidate['rated_apps']):,} < 5); neutral fallback",
        "gap": f"Approximate lower-bound HHI: {candidate['market_gap_hhi']:.3f}"
        if pd.notna(candidate["market_gap_hhi"])
        else "Missing/invalid; neutral fallback",
        "feasibility": "Fixed neutral 0.50 assumption; not data-derived",
    }
    rows = []
    for name, label in COMPONENT_LABELS.items():
        rows.append(
            {
                "Component": label,
                "Observed input / policy": metrics[name],
                "Normalized subscore": float(candidate[f"{name}_score"]),
                "Applied weight": weights[name] / sum(weights.values()),
                "Weighted contribution": float(candidate[f"{name}_contribution"]),
                "Evidence available": bool(candidate[f"{name}_available"]),
            }
        )
    return pd.DataFrame(rows)


def show_opportunity_finder(
    summary: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    st.title("Opportunity Finder")
    st.caption(
        "A transparent shortlist of categories to investigate—not five apps predicted to succeed."
    )
    with st.container(border=True):
        st.markdown("**How a category becomes a candidate**")
        st.markdown(
            "1. Start from cleaned, analysis-eligible app listings.  2. Aggregate category metrics.  3. Normalize the supported demand, competition, satisfaction, and concentration indicators across categories.  4. Apply the active normalized weights; unknown empirical features receive a clearly marked neutral 0.50, and feasibility is always a neutral engineering assumption.  5. Rank the categories, then attach a product concept as a human-validation hypothesis."
        )
        st.caption(
            "This dataset describes historical listings. It cannot identify a specific unmet need, forecast success, or establish current demand."
        )

    weights = _weight_controls()
    if not weights:
        return pd.DataFrame(), []
    ranked = score_opportunities(summary, weights)
    if ranked.empty:
        show_empty("No categories can be scored from the available eligible data.")
        return ranked, []
    profiles = recommendation_details(ranked)
    top = ranked.head(5).copy()

    st.subheader("Ranked candidates")
    st.write(
        "Scores are 0–1 weighted heuristic values. Table values update immediately with the controls above."
    )
    fig = px.bar(
        top.sort_values("score"),
        x="score",
        y="category",
        orientation="h",
        color="score",
        color_continuous_scale=["#DCE8EB", ACCENT],
        labels={"score": "Heuristic score (0–1)", "category": "Candidate category"},
        title="Top five category research candidates",
        hover_data={
            "app_count": ":,",
            "median_installs_lower_bound": ":,.0f",
            "evidence_coverage": ":.0%",
        },
    )
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(style_chart(fig, 340), width="stretch")

    component_names = list(DEFAULT_WEIGHTS)
    component_labels = {key: COMPONENT_LABELS[key] for key in component_names}
    contribution = top[
        ["category"] + [f"{key}_contribution" for key in component_names]
    ].rename(
        columns={
            f"{key}_contribution": component_labels[key] for key in component_names
        }
    )
    contribution = contribution.melt(
        id_vars="category",
        var_name="Weighted component",
        value_name="Score contribution",
    )
    fig = px.bar(
        contribution,
        x="category",
        y="Score contribution",
        color="Weighted component",
        title="How each factor contributes to each candidate score",
        labels={"category": "Candidate category"},
        color_discrete_sequence=["#176B87", "#6A9E9A", "#A6B9C0", "#D49A3A", "#687782"],
    )
    st.plotly_chart(style_chart(fig, 360), width="stretch")
    st.caption(
        "Each stacked bar sums to the displayed final score. Feasibility contributes a constant 0.5 × its normalized weight and does not distinguish categories."
    )

    table = top[
        [
            "category",
            "app_count",
            "median_installs_lower_bound",
            "mean_rating",
            "rating_coverage",
            "score",
            "evidence_coverage",
            "confidence",
        ]
    ].rename(
        columns={
            "category": "Category",
            "app_count": "Eligible apps",
            "median_installs_lower_bound": "Median install lower bound / app",
            "mean_rating": "Mean rating / 5",
            "rating_coverage": "Rating coverage",
            "score": "Score / 1",
            "evidence_coverage": "Empirical evidence coverage",
            "confidence": "Evidence confidence",
        }
    )
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "Median install lower bound / app": st.column_config.NumberColumn(
                format="localized"
            ),
            "Mean rating / 5": st.column_config.NumberColumn(format="%.2f"),
            "Rating coverage": st.column_config.NumberColumn(format="percent"),
            "Score / 1": st.column_config.NumberColumn(format="%.3f"),
            "Empirical evidence coverage": st.column_config.NumberColumn(
                format="percent"
            ),
        },
    )
    st.download_button(
        "Export ranked opportunities and component scores",
        export_csv_bytes(top),
        file_name="ranked_opportunities.csv",
        mime="text/csv",
        key="export_opportunities",
    )

    st.subheader("Weight sensitivity")
    sensitivity = sensitivity_analysis(summary)
    pivot = sensitivity.pivot(index="category", columns="scenario", values="rank")
    st.dataframe(
        pivot,
        width="stretch",
        column_config={
            col: st.column_config.NumberColumn(format="%d") for col in pivot.columns
        },
    )
    changes = sensitivity[sensitivity["scenario"].ne("baseline")][
        ["scenario", "category", "score_change", "baseline_rank", "rank", "rank_change"]
    ]
    st.caption(
        "Rank 1 is best. A negative rank change means the candidate moved upward; a positive value means it fell. All scenarios use the same score function and differ only in weights."
    )
    with st.expander("See score and rank changes by scenario"):
        st.dataframe(changes, hide_index=True, width="stretch")

    st.subheader("Why a candidate ranked here")
    candidate_categories = top["category"].tolist()
    selected = st.selectbox(
        "Candidate profile", candidate_categories, key="opportunity_candidate"
    )
    candidate = ranked[ranked["category"].eq(selected)].iloc[0]
    profile = next(item for item in profiles if item["category"] == selected)
    explanation = explain_candidate(candidate, weights)
    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        st.markdown(f"### {profile['concept']}")
        st.write(
            f"**Category:** {selected.replace('_', ' ').title()} · **Score:** {candidate['score']:.3f}/1 · **Empirical evidence coverage:** {candidate['evidence_coverage']:.0%}"
        )
        st.write(f"**Measured evidence:** {explanation['evidence']}")
        st.write(f"**Competition concern:** {explanation['competition_concern']}")
        st.write(
            f"**Largest observed component contribution:** {explanation['strongest']}"
        )
        st.write(
            f"**Weakest observed component contribution:** {explanation['weakest']}"
        )
        st.write(f"**Unavailable or insufficient evidence:** {explanation['missing']}")
        st.caption(
            f"{explanation['confidence']}. Product-opportunity confidence remains low until direct user validation."
        )
        st.markdown(f"**Problem hypothesis:** {profile['problem_hypothesis']}")
        st.markdown(
            f"**Potential differentiation (hypothesis):** {profile['potential_differentiation']}"
        )
    with col_right:
        st.markdown("**Score reconciliation**")
        components = _component_table(candidate, weights)
        st.dataframe(
            components,
            hide_index=True,
            width="stretch",
            column_config={
                "Normalized subscore": st.column_config.NumberColumn(format="%.3f"),
                "Applied weight": st.column_config.NumberColumn(format="percent"),
                "Weighted contribution": st.column_config.NumberColumn(format="%.3f"),
            },
        )
        st.write(
            f"**Contribution sum:** {components['Weighted contribution'].sum():.3f} = **final score {candidate['score']:.3f}**"
        )

    with st.container(border=True):
        a, b = st.columns(2)
        with a:
            st.markdown("**MVP starting scope · hypothesis**")
            for feature in profile["mvp_features"]:
                st.markdown(f"- {feature}")
            st.markdown("**Postpone**")
            for feature in profile["postpone"]:
                st.markdown(f"- {feature}")
        with b:
            st.markdown("**Validate before investing**")
            for step in profile["validation"]:
                st.markdown(f"- {step}")
            st.markdown("**Key risks and gaps**")
            for risk in profile["risks"]:
                st.markdown(f"- {risk}")
            st.markdown(
                f"**Monetization hypothesis:** {profile['monetization_hypothesis']}"
            )
            st.markdown(
                f"**Implementation complexity:** {profile['implementation_complexity']}"
            )

    with st.expander("Scoring definitions and missing-feature policy"):
        st.markdown(
            "**Final score** = Σ(component subscore × active normalized weight). All components use min-max scaling across the 33 eligible categories; all scores are relative to this candidate set."
        )
        st.markdown(
            "- **Demand:** log of median per-app install-band lower bound; higher is stronger evidence in this snapshot.\n- **Competitive accessibility:** inverse app count; fewer listings scores higher.\n- **Satisfaction:** mean observed rating, used only when at least five listings have ratings; ratings do not imply retention or willingness to pay.\n- **Market-gap proxy:** inverse install-lower-bound HHI; lower estimated concentration scores higher. It is not an unmet-need metric.\n- **Feasibility:** fixed neutral 0.50 human-assumption input; it cannot rank categories and is not inferred from the data."
        )
        st.markdown(
            "Missing empirical components receive a neutral 0.50 subscore and appear in the availability/coverage fields—not zero and not an implied positive finding. Empirical coverage is the share of active empirical weight with an observed usable metric, excluding feasibility. Install demand and HHI use the same install-band data and can partially double-count related evidence."
        )
    return ranked, profiles


def show_build_plan(ranked: pd.DataFrame, profiles: list[dict[str, Any]]) -> None:
    st.title("Build Plan")
    st.caption(
        "Turn a research candidate into a small validation-first plan. Product statements are hypotheses, not dataset facts."
    )
    if ranked.empty or not profiles:
        show_empty(
            "Rank at least one candidate on Opportunity Finder before creating a plan."
        )
        return
    choices = [profile["category"] for profile in profiles]
    selected = st.selectbox(
        "Choose an opportunity to plan", choices, key="build_plan_candidate"
    )
    profile = next(item for item in profiles if item["category"] == selected)
    st.subheader(profile["concept"])
    st.write(f"**Target audience hypothesis:** {profile['target_audience']}")
    st.write(f"**Problem hypothesis:** {profile['problem_hypothesis']}")
    st.info(
        f"Catalog evidence for {selected}: {profile['evidence_summary']} This score is a relative screening heuristic, not a forecast."
    )
    left, right = st.columns(2)
    with left:
        st.markdown("**First-version scope**")
        for item in profile["mvp_features"]:
            st.markdown(f"- {item}")
        st.markdown("**Explicitly out of scope**")
        for item in profile["postpone"]:
            st.markdown(f"- {item}")
    with right:
        st.markdown("**Validation before substantial build**")
        for index, item in enumerate(profile["validation"], start=1):
            st.markdown(f"{index}. {item}")
        st.markdown("**Success measures to define before testing**")
        st.markdown(
            "- Interview evidence for a repeated, specific user problem.\n- Prototype task completion and points of confusion.\n- Opt-in pilot use and qualitative usefulness.\n- Reliability and crash-free sessions."
        )
    with st.expander("Suggested milestones and technical starting point"):
        st.markdown(
            "1. Discovery interviews and workflow definition.\n2. Paper/clickable prototype and usability checks.\n3. Narrow Android implementation.\n4. Consented opt-in pilot.\n5. Review evidence; iterate, narrow, or stop against pre-agreed criteria."
        )
        st.markdown(
            "**Engineering suggestion (not dataset evidence):** Kotlin + Jetpack Compose for native Android. Prefer a local-first prototype if the workflow allows it. Add account systems, cloud sync, analytics SDKs, or third-party APIs only when validated requirements justify them."
        )
    st.markdown("**Risks and evidence gaps**")
    for item in profile["risks"]:
        st.markdown(f"- {item}")
    plan = build_plan_markdown(profile)
    st.download_button(
        "Download this plan as Markdown",
        plan.encode("utf-8"),
        file_name=f"{selected.lower()}_mvp_research_plan.md",
        mime="text/markdown",
        key="download_plan",
    )


def show_methodology(quality: dict[str, Any]) -> None:
    st.subheader("Methodology & data quality")
    st.caption(
        "Definitions and provenance for the evidence shown throughout the application."
    )
    st.markdown(
        "**Source:** [Kaggle · Google Play Store Apps](https://www.kaggle.com/datasets/lava18/google-play-store-apps), dataset ID `lava18/google-play-store-apps`. The bundled `license.txt` states CC BY 3.0 Unported; this conflicts with the brief's CC BY-SA 4.0 reference, so confirm Kaggle's current terms before redistribution. The pipeline retrieval timestamp is not an observation collection date."
    )
    with st.expander("Cleaning and eligibility rules", expanded=True):
        st.markdown(
            "- Original fields are preserved alongside parsed values. Ratings outside 1–5 become missing.\n- Install bands such as `1,000+` are retained verbatim and separately parsed as lower bounds.\n- Malformed numeric fields remain missing, not guessed. Size is normalized to MB; variable device sizes remain missing.\n- Duplicate names are reported but never removed based on name. Exact duplicate rows are retained in processed output; only repeated copies after the first are excluded from analysis.\n- A malformed category that does not match the source category convention is retained and flagged but excluded from category comparisons.\n- Update dates are catalog metadata, not app release dates or a time series."
        )
        st.json(
            {
                key: quality.get(key)
                for key in [
                    "raw_rows",
                    "cleaned_rows",
                    "analysis_eligible_rows",
                    "exact_duplicate_rows",
                    "duplicate_app_names",
                    "invalid_category_rows",
                    "missing_or_invalid_rating_rows",
                    "invalid_install_rows",
                    "invalid_review_rows",
                    "invalid_price_rows",
                    "unparseable_size_rows",
                    "invalid_date_rows",
                    "missing_percent_by_column",
                ]
            }
        )
    with st.expander("Metric definitions and interpretation"):
        st.markdown(
            "- **Eligible app count:** non-exact-duplicate source rows with a category matching the observed source convention.\n- **Median install lower bound per app:** median of parsed install-band lower bounds; not exact installs. Category totals are not used alone to rank opportunities.\n- **Rating coverage:** eligible records with a valid 1–5 rating divided by eligible records.\n- **Approximate concentration HHI:** sum of squared shares of install-band lower bounds in a category; coarse bands mean this is not precise market share.\n- **Candidate screening signal:** geometric mean of demand percentile and inverse app-count percentile; a triage aid, not an unmet-needs estimate.\n- **Opportunity score:** weighted sum of candidate-relative normalized component scores; category set and heuristic weights affect rank."
        )
    st.markdown(
        "**Limitations:** listings, ratings, reviews, and install bands do not measure revenue, retention, acquisition costs, customer pain points, competitor roadmaps, or current demand. Selection bias and missingness affect interpretation. Correlations do not establish causes. See `docs/METHODOLOGY.md` and `docs/KNOWN_LIMITATIONS.md` for detail."
    )


try:
    data, quality = get_data(os.environ.get("PLAYSTORE_DATA_DIR"))
except (RuntimeError, FileNotFoundError, ValueError, OSError) as exc:
    st.title("PlayStore Intelligence")
    st.error(f"The app catalog could not be loaded: {exc}")
    st.markdown(
        "Download with `.venv\\Scripts\\python.exe -m playstore_intelligence.pipeline --download` (with `PYTHONPATH=src`), or place the official app catalog CSV in `data/raw/`. Kaggle authentication stays local; never paste credentials into the app or commit them."
    )
    st.stop()

analysis_data = data.loc[data["analysis_eligible"]].copy()
summary = get_category_summary(analysis_data)

with st.sidebar:
    st.title("PlayStore\nIntelligence")
    st.caption("Market evidence → product research")
    page = st.radio("Research journey", PAGES, key="research_page")
    st.divider()
    st.caption("Historical Kaggle catalog · not live store data")
    st.caption(
        f"{len(analysis_data):,} eligible listings · {analysis_data['category'].nunique()} categories"
    )

if page == "Market Overview":
    show_market_overview(analysis_data, quality)
    show_methodology(quality)
elif page == "Explore Categories":
    show_category_explorer(analysis_data)
elif page == "Competition & Gaps":
    show_competition(analysis_data, summary)
elif page == "Opportunity Finder":
    ranked, profiles = show_opportunity_finder(summary)
    st.session_state["latest_ranked"] = ranked
    st.session_state["latest_profiles"] = profiles
else:
    ranked = st.session_state.get("latest_ranked", score_opportunities(summary))
    profiles = st.session_state.get("latest_profiles", recommendation_details(ranked))
    show_build_plan(ranked, profiles)

st.divider()
st.caption(
    "Decision support based on a historical listing snapshot. Validate user problems and demand independently before building."
)

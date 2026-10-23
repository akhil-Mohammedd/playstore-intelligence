"""PlayStore Intelligence interactive dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import streamlit as st

from playstore_intelligence.analytics import category_summary, overview
from playstore_intelligence.cleaning import clean_apps
from playstore_intelligence.data_loader import (
    discover_csvs,
    find_app_csv,
    find_dataset_dir,
    load_app_data,
)
from playstore_intelligence.opportunity_scoring import (
    DEFAULT_WEIGHTS,
    score_opportunities,
    sensitivity_analysis,
)
from playstore_intelligence.recommendations import recommendation_details

st.set_page_config(page_title="PlayStore Intelligence", page_icon="📊", layout="wide")
st.title("PlayStore Intelligence")
st.caption("Historical Google Play catalog analysis · decision support, not a forecast")


@st.cache_data(show_spinner="Loading and validating Google Play data…")
def get_data() -> tuple[pd.DataFrame, dict]:
    local = Path(__file__).resolve().parent / "data" / "raw"
    try:
        source_dir = find_dataset_dir(
            local if local.exists() and list(local.rglob("*.csv")) else None
        )
        raw = load_app_data(find_app_csv(discover_csvs(source_dir)))
        return clean_apps(raw)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise RuntimeError(
            f"Could not load the Kaggle dataset. Download/process it with `python -m playstore_intelligence.pipeline --download` or place the CSV under data/raw. Details: {exc}"
        ) from exc


try:
    data, quality = get_data()
except RuntimeError as exc:
    st.error(str(exc))
    st.info(
        "Dataset source: https://www.kaggle.com/datasets/lava18/google-play-store-apps. KaggleHub uses your local Kaggle authentication; alternatively download the CSV from Kaggle and place it in data/raw."
    )
    st.stop()

analysis_data = data.loc[data["analysis_eligible"]].copy()
summary = category_summary(analysis_data)
metrics = overview(analysis_data, quality)
sections = [
    "Overview",
    "Category Explorer",
    "Competition Analysis",
    "Opportunity Finder",
    "App Explorer",
    "Methodology",
]
section = st.sidebar.radio("Explore", sections)
st.sidebar.caption("Source: Kaggle · lava18/google-play-store-apps")

if section == "Overview":
    cols = st.columns(4)
    cols[0].metric("App records", f"{metrics['app_rows']:,}")
    cols[1].metric("Categories", f"{metrics['categories']:,}")
    cols[2].metric("Rating coverage", f"{metrics['rating_coverage']:.1%}")
    cols[3].metric("Free listings", f"{metrics['free_share']:.1%}")
    st.warning(
        "Install values are lower-bound estimates parsed from historical install bands; this snapshot cannot establish current trends or causation."
    )
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            px.bar(
                summary.sort_values("app_count", ascending=False),
                x="category",
                y="app_count",
                title="Observed apps by category",
            ),
            width="stretch",
        )
    with right:
        st.plotly_chart(
            px.histogram(
                data.dropna(subset=["rating"]),
                x="rating",
                nbins=20,
                title="Observed rating distribution",
            ),
            width="stretch",
        )
    st.subheader("Data quality")
    st.json(quality)
elif section == "Category Explorer":
    categories = sorted(analysis_data["category"].dropna().unique())
    selected = st.multiselect("Categories", categories, default=categories[:5])
    subset = analysis_data[analysis_data["category"].isin(selected)]
    search = st.text_input("Search app names")
    if search:
        subset = subset[subset["app"].str.contains(search, case=False, na=False)]
    st.dataframe(
        subset[
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
        ],
        width="stretch",
    )
    st.download_button(
        "Download filtered CSV",
        subset.to_csv(index=False).encode("utf-8"),
        "filtered_apps.csv",
        "text/csv",
    )
    st.plotly_chart(
        px.box(
            subset.dropna(subset=["rating"]),
            x="category",
            y="rating",
            title="Ratings by selected category",
        ),
        width="stretch",
    )
elif section == "Competition Analysis":
    st.caption(
        "Concentration uses squared shares of parsed install-band lower bounds; it is an approximate snapshot indicator, not precise market share."
    )
    st.plotly_chart(
        px.scatter(
            summary,
            x="app_count",
            y="median_installs_lower_bound",
            size="app_count",
            color="estimated_install_hhi",
            hover_name="category",
            title="Category competition and median install-band lower bound",
        ),
        width="stretch",
    )
    st.dataframe(
        summary.sort_values("estimated_install_hhi", ascending=False),
        width="stretch",
    )
elif section == "Opportunity Finder":
    st.caption(
        "Heuristic category screening. Concepts are research prompts; this data does not measure unmet need, current demand, or likelihood of success."
    )
    weights = {}
    for key, default in DEFAULT_WEIGHTS.items():
        weights[key] = st.sidebar.slider(
            f"{key.title()} weight", 0.0, 1.0, float(default), 0.05
        )
    if sum(weights.values()) == 0:
        st.error("Increase at least one scoring weight.")
        st.stop()
    ranked = score_opportunities(summary, weights)
    top = ranked.head(5)
    st.dataframe(
        top[
            [
                "category",
                "app_count",
                "median_installs_lower_bound",
                "mean_rating",
                "estimated_install_hhi",
                "score",
                "confidence",
            ]
        ],
        width="stretch",
    )
    st.download_button(
        "Export ranked categories",
        top.to_csv(index=False).encode("utf-8"),
        "opportunity_scores.csv",
        "text/csv",
    )
    st.subheader("Alternative-weight sensitivity")
    st.dataframe(sensitivity_analysis(summary), width="stretch")
    for item in recommendation_details(ranked):
        with st.expander(item["concept"]):
            for key, value in item.items():
                if key != "concept":
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
elif section == "App Explorer":
    search = st.text_input("App name contains")
    subset = (
        data
        if not search
        else data[data["app"].str.contains(search, case=False, na=False)]
    )
    st.dataframe(
        subset[
            [
                "app",
                "category",
                "genres",
                "rating",
                "reviews",
                "installs_raw",
                "price_usd",
                "size_mb",
                "last_updated",
            ]
        ].head(500),
        width="stretch",
    )
    st.caption(
        "Showing up to 500 matching rows; blank metrics are missing/invalid, not zero."
    )
else:
    st.markdown("""### Source and licence
[Kaggle: Google Play Store Apps](https://www.kaggle.com/datasets/lava18/google-play-store-apps), dataset ID `lava18/google-play-store-apps`. The downloaded bundle's `license.txt` says CC BY 3.0 Unported, conflicting with the CC BY-SA 4.0 reference in the project brief. The current Kaggle listing was not textually verifiable during this run. Retain attribution and verify the listing's current terms before redistribution. Retrieval date is recorded by each pipeline run; source observation dates are historical and not a time series.

### Methods
Install text such as `1,000+` is parsed as a lower-bound estimate while the source band is preserved. Ratings outside 1–5 become missing. Duplicate names are reported but retained. Category summaries include both total lower-bound installs and median per-app lower bound. Competition HHI uses those lower bounds and is approximate. Opportunity scores are min-max normalized heuristics with user-adjustable weights; the feasibility input is intentionally neutral pending independent implementation research. No causal or commercial success claims are made.

### Limitations
Coverage and inclusion are dataset-specific; app records and ratings do not measure current user demand, unmet needs, retention, revenue, or store ranking today. Historical install bands and ratings are subject to selection, reporting, and missingness bias. Concept-specific demand needs primary user research.
""")

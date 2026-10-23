"""Hypothesis-led concept profiles attached to ranked data categories."""

from __future__ import annotations

from typing import Any

import pandas as pd

CONCEPTS = {
    "EDUCATION": {
        "concept": "Study Session Planner",
        "target_audience": "Students preparing for recurring study or revision sessions (audience hypothesis).",
        "problem": "Students may need a lighter way to plan focused sessions and revision reminders; the dataset does not measure this problem.",
        "differentiation": "A narrow, low-friction study-session flow is a product hypothesis; validate against actual alternatives users name.",
        "mvp": [
            "Create a study session",
            "Add a short topic checklist",
            "Review a simple session history",
        ],
        "postpone": [
            "Social learning features",
            "AI-generated study content",
            "Paid acquisition",
        ],
        "validation": [
            "Interview students about recent study planning",
            "Prototype a session-planning task",
            "Test willingness to return to a paper prototype",
        ],
    },
    "SHOPPING": {
        "concept": "Purchase Comparison Notebook",
        "target_audience": "Shoppers comparing a small set of products before purchase (audience hypothesis).",
        "problem": "Shoppers may want a private place to compare saved product details; the dataset contains no feature or unmet-need evidence.",
        "differentiation": "A user-controlled comparison notebook is a hypothesis; check whether target users already solve this with existing tools.",
        "mvp": [
            "Save a product note",
            "Compare a small number of user-entered attributes",
            "Set an optional reminder",
        ],
        "postpone": [
            "Retailer integrations",
            "Price scraping",
            "Affiliate monetization",
        ],
        "validation": [
            "Interview shoppers about a recent comparison",
            "Test a manual comparison prototype",
            "Check whether participants voluntarily reuse it",
        ],
    },
    "WEATHER": {
        "concept": "Weather-Aware Routine Planner",
        "target_audience": "People who plan a recurring outdoor routine (audience hypothesis).",
        "problem": "Some people may want to align a routine with weather conditions; this need is not measured by the listing dataset.",
        "differentiation": "A simple routine-first presentation is an unverified hypothesis; weather API accuracy and existing apps must be researched.",
        "mvp": [
            "Choose one recurring outdoor routine",
            "Show a forecast-informed planning prompt",
            "Allow a simple manual fallback",
        ],
        "postpone": [
            "Complex forecasts",
            "Wearable integrations",
            "Always-on location tracking",
        ],
        "validation": [
            "Interview people with a specific outdoor routine",
            "Test a clickable planning flow",
            "Verify demand and data-source terms before API integration",
        ],
    },
    "PHOTOGRAPHY": {
        "concept": "Photo Workflow Organizer",
        "target_audience": "Mobile photographers managing a repeatable capture or editing workflow (audience hypothesis).",
        "problem": "Photographers may want to organize a repeatable workflow; catalog data contains no workflow or feature-level feedback.",
        "differentiation": "A focused checklist rather than an editing suite is a hypothesis; validate against camera/gallery tools people already use.",
        "mvp": [
            "Create a reusable capture checklist",
            "Save a session note",
            "Review a simple workflow history",
        ],
        "postpone": ["Image processing", "Cloud photo storage", "Social publishing"],
        "validation": [
            "Observe photographers prepare for a session",
            "Prototype the checklist flow",
            "Test whether it reduces missed steps without handling image files",
        ],
    },
    "SOCIAL": {
        "concept": "Small-Group Event Planner",
        "target_audience": "Small groups coordinating a recurring shared event (audience hypothesis).",
        "problem": "Small groups may need lightweight coordination; ratings and install bands do not confirm this unmet need.",
        "differentiation": "A deliberately small-group planning workflow is a hypothesis; map existing messaging/calendar alternatives with interviewees.",
        "mvp": [
            "Create a basic event plan",
            "Collect participant availability manually",
            "Show one shared checklist",
        ],
        "postpone": [
            "Public social feeds",
            "Contact harvesting",
            "Complex chat and recommendation systems",
        ],
        "validation": [
            "Interview organizers about their last event",
            "Test a plan-and-confirm prototype",
            "Measure whether a group completes a real task with consent",
        ],
    },
    "GAME": {
        "concept": "Casual Game Research Prototype",
        "target_audience": "A narrow player segment to be defined through playtesting (not identifiable from category totals).",
        "problem": "The app catalog cannot reveal preferred game mechanics or player pain points; a mechanic hypothesis must come from playtesting.",
        "differentiation": "No differentiation is evidenced by this dataset; identify it through competitor play and user observation.",
        "mvp": [
            "Prototype one core mechanic",
            "Add a short tutorial",
            "Measure consented playtest task completion",
        ],
        "postpone": ["Ads", "In-app purchases", "Live operations and multiplayer"],
        "validation": [
            "Observe target players test a paper or clickable prototype",
            "Compare comprehension across iterations",
            "Do not infer retention from installs or ratings",
        ],
    },
}


def recommendation_details(ranked: pd.DataFrame) -> list[dict[str, Any]]:
    """Create up to five research briefs using current scored rows and metrics."""
    output: list[dict[str, Any]] = []
    for _, row in ranked.head(5).iterrows():
        category = str(row["category"])
        template = CONCEPTS.get(
            category,
            {
                "concept": f"{category.replace('_', ' ').title()} Workflow Prototype",
                "target_audience": "A specific audience within this category; define through interviews.",
                "problem": "A narrow workflow problem is an unverified hypothesis; category data does not reveal unmet need.",
                "differentiation": "No product differentiation is established by category-level catalog metrics.",
                "mvp": [
                    "Interview target users",
                    "Prototype one narrow task",
                    "Test task completion before coding",
                ],
                "postpone": [
                    "Complex integrations",
                    "Paid acquisition",
                    "Broad feature expansion",
                ],
                "validation": [
                    "Interview users about recent behavior",
                    "Test a clickable prototype",
                    "Measure opt-in interest without claiming future demand",
                ],
            },
        )
        mean_rating = row.get("mean_rating")
        rating_text = (
            f"{float(mean_rating):.2f}/5 from {int(row['rated_apps']):,} rated listings"
            if pd.notna(mean_rating) and bool(row["rating_evidence_sufficient"])
            else f"not used (only {int(row['rated_apps']):,} rated listings; minimum threshold is 5)"
        )
        installs = row.get("median_installs_lower_bound")
        evidence_summary = (
            f"{int(row['app_count']):,} eligible listings in {category}; median install-band lower bound "
            f"{float(installs):,.0f} per listing; observed mean rating {rating_text}; "
            f"approximate install-lower-bound HHI {float(row['estimated_install_hhi']):.3f}"
            if pd.notna(installs) and pd.notna(row.get("estimated_install_hhi"))
            else f"{int(row['app_count']):,} eligible listings in {category}; one or more metrics unavailable."
        )
        output.append(
            {
                "concept": template["concept"],
                "category": category,
                "target_audience": template["target_audience"],
                "problem_hypothesis": template["problem"],
                "evidence_summary": evidence_summary,
                "demand_indicator": f"Median per-app install lower bound: {installs:,.0f}"
                if pd.notna(installs)
                else "Unavailable",
                "competition_indicator": f"{int(row['app_count']):,} eligible listings; approximate lower-bound HHI {row['estimated_install_hhi']:.3f}"
                if pd.notna(row.get("estimated_install_hhi"))
                else f"{int(row['app_count']):,} eligible listings; HHI unavailable",
                "potential_differentiation": template["differentiation"],
                "mvp_features": template["mvp"],
                "postpone": template["postpone"],
                "monetization_hypothesis": "Test willingness to pay only after a demonstrated user problem; no revenue estimate is supported by this dataset.",
                "implementation_complexity": "Not inferable from catalog metrics. Scope and integration requirements must be assessed after discovery.",
                "risks": [
                    "Historical, selective catalog snapshot",
                    "Install values are band lower bounds",
                    "No direct evidence of unmet needs, retention, revenue, or current demand",
                ],
                "validation": template["validation"],
                "score": float(row["score"]),
                "weighted_score": float(row["score"]),
                "demand_score": float(row["demand_score"]),
                "accessibility_score": float(row["accessibility_score"]),
                "satisfaction_score": float(row["satisfaction_score"]),
                "market_gap_score": float(row["gap_score"]),
                "feasibility_score": float(row["feasibility_score"]),
                "evidence_coverage": float(row["evidence_coverage"]),
                "missing_components": str(row["missing_components"]),
                "confidence": str(row["confidence"]),
            }
        )
    return output

"""Cautious concept framing for categories with measurable evidence."""

from __future__ import annotations

import pandas as pd


def recommendation_details(ranked: pd.DataFrame) -> list[dict]:
    """Create five explicitly provisional category research briefs."""
    hypotheses = {
        "EDUCATION": (
            "Study Session Planner",
            "Students may benefit from a focused study-session and revision planner; unmet need is unverified.",
        ),
        "SHOPPING": (
            "Purchase Comparison Notebook",
            "Shoppers may want a private way to compare saved products and purchase notes; unmet need is unverified.",
        ),
        "WEATHER": (
            "Weather-Aware Routine Planner",
            "Outdoor workers or commuters may value planning routines around forecasts; unmet need is unverified.",
        ),
        "PHOTOGRAPHY": (
            "Photo Workflow Organizer",
            "Mobile photographers may want a lightweight way to organize capture workflows; unmet need is unverified.",
        ),
        "SOCIAL": (
            "Small-Group Event Planner",
            "Small communities may need simpler coordination for shared events; unmet need is unverified.",
        ),
        "GAME": (
            "Casual Game Research Prototype",
            "A narrow casual-game mechanic is a product hypothesis requiring playtesting; this catalog does not reveal mechanic-level demand.",
        ),
    }
    output = []
    for row in ranked.head(5).itertuples():
        category = row.category.replace("_", " ").title()
        concept, problem = hypotheses.get(
            row.category,
            (
                f"{category} Workflow Prototype",
                f"A narrow workflow in {category} is a product hypothesis; interview users to identify an actual pain point.",
            ),
        )
        output.append(
            {
                "concept": f"{concept} (hypothesis)",
                "category": row.category,
                "target_audience": "A narrowly defined audience within this category; identify and verify via interviews.",
                "problem_hypothesis": problem,
                "evidence": f"{int(row.app_count)} observed app records; median install-band lower bound {row.median_installs_lower_bound:,.0f}; mean observed rating {row.mean_rating:.2f}"
                if pd.notna(row.mean_rating)
                else f"{int(row.app_count)} observed app records; rating evidence unavailable or insufficient.",
                "mvp": "Interview 8–12 target users, prototype the named workflow, and test task completion plus opt-in interest before development.",
                "postpone": "Paid acquisition, complex integrations, and broad feature sets until demand is validated.",
                "monetization_hypothesis": "Freemium or one-time purchase are hypotheses only; test willingness to pay.",
                "difficulty": "Unknown; estimate after scope, platform, and integration discovery.",
                "risks": "Historical catalog snapshot; install bands are lower bounds; data does not measure current demand or unmet needs.",
                "validation": "Conduct 8–12 target-user interviews, test a prototype task, and measure opt-in interest before committing to build.",
                "demand_score": round(float(row.demand), 3),
                "accessibility_score": round(float(row.accessibility), 3),
                "satisfaction_score": round(float(row.satisfaction), 3),
                "market_gap_score": round(float(row.gap), 3),
                "feasibility_score": round(float(row.feasibility), 3),
                "weighted_score": round(float(row.score), 3),
                "confidence": row.confidence,
            }
        )
    return output

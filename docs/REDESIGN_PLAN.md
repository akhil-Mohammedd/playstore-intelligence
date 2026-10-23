# UI/UX redesign plan

## Baseline audit

- Entry point: `app.py`; cleaned data comes from KaggleHub cache/local `data/raw` via `data_loader.py` and `cleaning.py`.
- Analytics: `analytics.category_summary`; ranking: `opportunity_scoring.score_opportunities`; concept text: `recommendations.recommendation_details`.
- Baseline tests: `pytest -q` passed (7 tests) before redesign.
- Current UI had six loosely organized radio destinations, minimal narrative context, an unfiltered competition page, raw JSON quality output, wide app tables, and generic recommendation accordions.
- Scoring normalized weights but silently substituted neutral values for missing evidence; feasibility was fixed at 0.5. It did not expose weighted contributions, empirical coverage, or candidate-level explanation.
- Existing Streamlit AppTest and a previous local HTTP health check passed. Browser automation/screenshot tools are not available in this workspace.

## Implemented information architecture

1. **Market Overview** — four concise KPIs, category distribution, source install-band distribution, computed observations with denominators/limitations, optional rating/review/free-paid details, and cleaning methodology.
2. **Explore Categories** — all-category toggle, selected categories, listing-type/rating/install/app-name/minimum-volume filters, live category comparison, category profile, compact app table, filtered CSV export, and reset behavior.
3. **Competition & Gaps** — demand-proxy versus listing-count scatter, concentration context, screening signal comparison, selected-category evidence versus overall medians, and explicit research next steps.
4. **Opportunity Finder** — visible scoring pipeline, live weights/reset, normalized active-weight table, final score, component scores/contributions, data coverage, missing-feature disclosure, candidate explanation, alternative scenario rank/score changes, and ranked CSV export.
5. **Build Plan** — selected candidate becomes a hypothesis-labeled MVP/validation plan with milestones, scope exclusions, engineering suggestions, and downloadable Markdown.

## Recommendation-engine changes

- Keep category-level candidate-relative min-max heuristics and default weights 30/25/20/15/10.
- Expose transformed component scores, raw metric context, normalized active weight, and weighted contribution; final score is their sum, clipped to [0,1].
- Name competitive accessibility direction: fewer eligible listings scores higher.
- Ratings are only scored when at least five listings have ratings.
- Missing empirical signals use visible neutral 0.50 values; feasibility is explicitly fixed at 0.50 and never data-derived.
- Report empirical evidence coverage as available active empirical weight divided by active empirical weight (excluding feasibility).
- Generate explanations from real values; concepts and user problems remain labeled hypotheses.
- Alternative scenarios use the same scoring function and report baseline ranks and score changes.

## Verification and acceptance

- Synthetic and Streamlit AppTests: 13 passed after redesign.
- AppTest exercised all five pages, empty category selection/reset, all-category selection, live weight-driven score/rank changes, and restoring defaults.
- Ruff checks, formatting, and `pip check` passed.
- Real downloaded-data ranking remains Education, Shopping, Weather, Photography, Social for defaults; alternative scenarios exchange Photography/Social. This is evidence of limited rank sensitivity, not product-success confidence.
- No live browser or screenshot inspection was available; AppTest and local HTTP server checks substitute for UI behavior/smoke verification.

# Sprint plan

## Sprint 1 — Ingestion and data quality
- Discover KaggleHub/cache or local CSV, validate expected app schema, preserve originals, clean safely, report invalid/missing/duplicate values.
- Exit: synthetic unit tests pass and actual dataset pipeline creates reproducible processed output.

## Sprint 2 — Descriptive analysis
- Summarize category volume, install lower bounds, ratings, reviews, free share, and approximate concentration. Interpret as historical observational evidence only.
- Exit: calculations have manually checked unit examples; actual findings documented only after pipeline execution.

## Sprint 3 — Opportunity research
- Rank categories with transparent configurable heuristics and compare alternative weights. Generate provisional concepts; demand claims require validation.
- Exit: deterministic scores, no unsupported commercial claims.

## Sprint 4 — Dashboard
- Ship Overview, Category Explorer, Competition, Opportunity Finder, App Explorer, and Methodology.
- Exit: Streamlit smoke run and no fabricated KPI values.

## Sprint 5 — Verification
- Run pytest, Ruff, dependency checks, pipeline, dashboard smoke tests, CI syntax review.
- Exit: tests/results captured in TEST_REPORT.

## Sprint 6/7 — Release preparation
- Finish user-facing docs and CI; initialize local Git only after reviewing working tree. Do not publish or deploy without authorization.

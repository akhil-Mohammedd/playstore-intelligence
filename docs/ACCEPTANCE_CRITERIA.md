# Acceptance criteria

- [x] Resolve the app CSV by schema, rather than hardcoded current directory.
- [x] Preserve original source fields and mark malformed/missing numerical values.
- [x] Preserve duplicates but exclude exact duplicate rows and invalid categories from market scoring.
- [x] Treat install counts as lower-bound bands and document HHI as approximate.
- [x] Category metrics include counts, lower-bound totals/medians, observed ratings, coverage, and concentration.
- [x] Opportunity ranking has validated configurable weights and alternative-weight comparisons.
- [x] App recommendations distinguish catalog evidence from hypotheses and include user validation actions.
- [x] Dashboard has the six requested sections and handles missing dataset gracefully.
- [x] Test suite runs without downloading external data; integration pipeline runs against the obtained Kaggle dataset.
- [ ] Live deployment and public GitHub repository (not authorized/configured).

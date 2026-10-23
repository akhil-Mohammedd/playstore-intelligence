# Engineering decisions

- Retain the user-managed `.venv`; install dependencies only inside it.
- KaggleHub cache is the default data location; local CSV folder is an explicit fallback. Raw download remains unmodified and outside Git.
- Use Pandas 2.3.3 after Pandas 3.1.0's native extension was blocked by Windows Application Control. Do not alter security policy.
- Keep every source row in cleaned output, flag exact duplicates and malformed category rows, and exclude only those from category aggregates. Similar app names are not deduplicated.
- Use install-band lower bounds for descriptive metrics and explicitly label estimates; no conversion to exact installations.
- Use neutral 0.5 feasibility because this dataset cannot infer implementation difficulty. Scores are heuristic, category-relative, and not success probabilities.
- The dataset cannot identify unmet user needs. App names and problem statements are framed as hypotheses, with validation tasks included.
- Do not initialize a remote or deploy without an authorized destination; local Git initialization is user-requested and may be done after ignore review.

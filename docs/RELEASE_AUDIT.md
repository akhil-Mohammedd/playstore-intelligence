# Release validation audit

Audit date: 2026-10-23. All Python checks used the existing Python 3.14.8 virtual environment at `.venv/Scripts/python.exe`.

## Release status

The local app and data pipeline are runnable and the automated suite, Ruff checks, and dependency consistency check pass. One material cleaning defect was found and fixed during this audit: compact Play Store app sizes such as `19M` and `512k` were previously counted as malformed. The project is **not yet a clean release candidate for GitHub publication**: the working tree already contained extensive redesign changes that were not committed despite the prior status description, there is no Git remote or deployment, and browser-level visual review and hosted CI have not been performed. No existing changes were discarded.

## Check register

| Check | Verification method | Actual result | Status | Defect found | Fix applied |
|---|---|---|---|---|---|
| Git baseline and history | `git status --short --branch`; `git log -5 --oneline --decorate`; `git remote -v` | Branch `master`; HEAD `06a61b0 Configure source path diagnostics`, preceded by `821700b Build PlayStore Intelligence analytics platform`; no remote. Redesign files were modified/untracked at audit start. | Pass with release caveat | Claimed committed redesign was not present in HEAD. | Preserved the worktree; did not reset, stage, or commit the unrelated redesign changes. |
| Environment/dependencies | `.venv/Scripts/python.exe --version`; dependency imports; `pip check` | Python 3.14.8; pandas 2.3.3, NumPy 2.5.4, Plotly 7.1.0, Streamlit 1.66.1, pytest 9.1.1; no broken requirements. | Pass | None found. | None. |
| Dataset source and schema | Run pipeline with `--dataset-dir dataset`; inspect `data/processed/data_quality.json` | Source `D:\optimization\DataAnalysing\dataset\googleplaystore.csv`, 10,841 rows, 13 columns. Bundle also has `googleplaystore_user_reviews.csv` (64,295 × 5) and `license.txt`. The app currently analyzes the app catalog only. | Pass | None. | None. |
| Raw preservation and reproducibility | Run pipeline against `dataset/`; inspect source path, loader, generated outputs, and resulting quality JSON | Pipeline reads `dataset/googleplaystore.csv` and writes derived files to ignored `data/processed/`; raw source remains present and unchanged by the pipeline code. Quality JSON reports the input directory and file. | Pass | None found. | None. |
| Cleaning and eligibility | `clean_apps` on raw catalog; inspect quality JSON after pipeline | 10,841 retained audit rows; 483 exact duplicate rows and 1 malformed-category row excluded from analysis; 10,357 analysis-eligible rows across 33 categories. 1,979 records share an app name; names are not used to deduplicate. | Pass | None found in duplicate policy. | None. |
| Size parsing | Inspect source `Size` values; compare quality output before/after parser correction | Source uses compact units including `19M` and `512k`; unparseable sizes fell from 9,146 to 1. “Varies with device” remains unavailable rather than fabricated. The one remaining unparseable value is not silently interpreted. | Pass after fix | Compact source suffixes `M` and `k` were not accepted. | `parse_size_mb` now handles compact and long unit forms and validates numeric syntax; regression tests added. |
| Invalid/missing values | Inspect generated quality JSON | 1,475 missing/invalid ratings, 1 malformed rating outside 1–5, 1 invalid install, 1 invalid review, 1 invalid price, and 1 invalid update date. `Installs=Free` occurs in the malformed shifted row; install parsing yields missing. | Pass | None additional found. | None. |
| Category metric manual check | Independently filter eligible Education rows from cleaned frame; calculate median installs, mean rating, median reviews | 130 eligible rows; median install lower bound 1,000,000; mean rating 4.3759689922; median reviews 17,283.5. `category_summary` returns matching values. | Pass | None. | None. |
| Install-band interpretation | Inspect `parse_installs`, source text retention, and category metric fields | `1,000+` is retained in `installs_raw`; numeric field is explicitly `estimated_installs_lower_bound`. Ranking uses a median of band lower bounds, not exact downloads. | Pass | Scores and concentration remain approximate because the underlying measures are banded. | No correction required; limitation documented. |
| Score pipeline | Run `category_summary` → `score_opportunities`; manually sum component contributions for first candidate | Score is category-relative min-max across the 33 eligible categories; weights normalize to 1; component contributions sum exactly to final score. Education worked example below. | Pass with limitation | Demand and inverse-HHI gap features both reuse install-band evidence; partial double-counting is possible. | Already documented in methodology and this audit; interpret scores as heuristic screening, not a validated predictor. |
| Missing score features | Test categories with low/no evidence; inspect availability, fallback, and coverage fields | Missing empirical components are explicitly flagged and receive neutral 0.50; evidence coverage is weighted availability of empirical features, excluding feasibility. Feasibility is always 0.50 and explicitly an engineering assumption. | Pass | Neutral imputation can affect scores when weights emphasize missing metrics. | Disclosure and per-candidate coverage are present; users should consider coverage when interpreting rankings. |
| Sensitivity | Run `sensitivity_analysis` on real category summary | Education, Shopping, Weather remain top three; Photography and Social exchange ranks 4/5 under equal-weight and demand-light scenarios. The same score function is used. | Pass | Lower two ranks are not robust to reasonable weight changes. | Sensitivity table and rank-change disclosure retained. |
| Recommendation derivation | Trace scored DataFrame through `recommendation_details`; inspect output rows and concept mapping | Five output concepts are attached to categories actually selected by the computed rank order. Names/features are category-specific editorial hypotheses; category evidence does not establish a specific product’s unmet need. | Pass with limitation | Concept templates are deliberately curated, not algorithmically discovered product features. | Their content labels hypotheses and provides validation experiments; no success forecast is made. |
| Automated tests | `.venv/Scripts/python.exe -m pytest -q` | 13 passed, including added compact size unit and malformed numeric cases, plus synthetic pipeline, filtering, score, export, and dashboard interactions. | Pass | No failures. | Added regression coverage for actual source units. |
| Ruff | `.venv/Scripts/ruff.exe check .`; `.venv/Scripts/ruff.exe format --check .` | All checks passed; 24 Python files formatted. | Pass | None. | None. |
| Streamlit page smoke | `AppTest.from_file('app.py')`; switch `research_page` across all five destinations using the workspace data | Market Overview, Explore Categories, Competition & Gaps, Opportunity Finder, Build Plan rendered with no AppTest exceptions. Synthetic tests separately exercise empty category results/reset, all-category selection, weight change/rank update, and reset. | Pass | Browser-level appearance was not observable in this environment. | No unsafe visual-only CSS changes made. |
| Streamlit running server | GET `http://127.0.0.1:8501/_stcore/health` and `/` | Health returned HTTP 200 `ok`; app root returned HTTP 200. | Pass | Does not prove visual correctness or every browser interaction. | AppTest complements HTTP smoke. |
| CSV and Markdown serialization | Unit tests for `export_csv_bytes` and `build_plan_markdown` | CSV bytes begin with expected category header; plan export includes actual selected profile evidence and hypothesis/validation language. | Pass | Browser download click itself not automated. | None. |
| Git ignore/release hygiene | `git check-ignore -v` on `.venv`, dataset, processed output, and log; `git ls-files` scan | `.venv`, local `dataset/`, `data/processed/` output, and `streamlit.log` are ignored. No dataset CSV or credential-like files are tracked. | Pass | Worktree is not clean; redesign edits predate this audit and remain uncommitted. | Preserved all existing modifications. |
| GitHub Actions | Inspect workflow and GitHub Actions API runs | Run 39903535968 for commit `048f9e1` completed successfully on `windows-latest` with Python 3.13. Dependency install, `pip check`, Ruff lint/format, and pytest passed. Updated checkout v5/setup-python v6 job has no failed steps. | Pass | None observed in the completed job. | Updated to official Node 24 action majors; both the workflow update and subsequent docs commit runs passed. |
| Visual/responsive review | Browser/UI inspection capability check; Streamlit AppTest used instead | No browser screenshot/interaction tool available. AppTest and HTTP smoke pass, but rendered visual quality, viewport responsiveness, and download browser behavior are not verified. | Not verified | Pixel-level and responsive issues could remain. | No claims of visual verification. |
| Streamlit deployment | Inspect repository and Streamlit configuration | GitHub repository is public and contains the app; no Streamlit Community Cloud app or verified live URL exists. | Not deployed | Hosted startup and interactions remain unverified. | KaggleHub cold-start fallback and actionable error are implemented and unit-tested; deploy manually to verify the host environment. |

## Actual data and ranking results

The pipeline used the repository-local source file at `dataset/googleplaystore.csv`, not synthetic findings. It identified 10,841 raw catalog rows, 483 exact duplicate rows, 1 malformed category row, and 10,357 analysis-eligible rows across 33 categories. Repeated app names were reported but retained. The downloaded review CSV was recorded as available but is not joined into the current category scoring.

After correcting compact size parsing, the quality report records one unparseable size (besides values explicitly marked `Varies with device`, which are not considered malformed). The report also identifies one malformed install/review/price/date value, and 1,475 missing or invalid ratings. Historical `Last Updated` is not interpreted as app launch date or a longitudinal trend.

Default score order from the implemented engine:

| Rank | Category / concept hypothesis | Eligible listings | Median install-band lower bound per listing | Mean rating (rated listings) | Approx. lower-bound HHI | Score |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Education — Study Session Planner | 130 | 1,000,000 | 4.376 | 0.0787 | 0.820529 |
| 2 | Shopping — Purchase Comparison Notebook | 224 | 1,000,000 | 4.251 | 0.0269 | 0.782288 |
| 3 | Weather — Weather-Aware Routine Planner | 82 | 1,000,000 | 4.244 | 0.0761 | 0.771376 |
| 4 | Photography — Photo Workflow Organizer | 322 | 3,000,000 | 4.183 | 0.0468 | 0.767726 |
| 5 | Social — Small-Group Event Planner | 280 | 1,000,000 | 4.255 | 0.0553 | 0.761064 |

These are category-derived research prompts, not five empirically identified products or predictions. The concept name and target-user/problem statements are hypotheses. Equal-weight and demand-light scenarios exchange Photography and Social. Close scores and category-relative min-max scaling make ordering sensitive to weight choices and the set of categories being compared.

## Worked score reproduction: Education

The default normalized weights are demand 0.30, accessibility 0.25, satisfaction 0.20, gap 0.15, feasibility 0.10. Education component values from the actual computed summary are:

| Component | Normalized score | Weight | Contribution |
|---|---:|---:|---:|
| Demand | 0.811015 | 0.30 | 0.243304 |
| Competitive accessibility | 0.959259 | 0.25 | 0.239815 |
| Observed satisfaction | 0.871541 | 0.20 | 0.174308 |
| Inverse-HHI gap proxy | 0.754009 | 0.15 | 0.113101 |
| Feasibility assumption | 0.500000 | 0.10 | 0.050000 |

`0.811015×0.30 + 0.959259×0.25 + 0.871541×0.20 + 0.754009×0.15 + 0.5×0.10 = 0.820529` (rounded). The unrounded contribution sum independently equals the engine's `0.8205288254020335`. Demand is based on log-scaled median install-band lower bound; accessibility is inverse app count; satisfaction uses category mean rating with at least five rated listings; gap is inverse concentration HHI from the same install lower bounds; feasibility is a constant 0.5 assumption. The shared install inputs across demand and HHI are a known overlap.

## Files changed during this validation

- `src/playstore_intelligence/cleaning.py` — parse compact `M`, `k`, and long-form size units; reject malformed numeric strings.
- `tests/test_pipeline.py` — add regression checks for `19M`, `512k`, decimal sizes, and malformed syntax.
- `docs/TEST_REPORT.md` — update verification details and corrected size-quality count.
- `docs/RELEASE_AUDIT.md` — this audit report.

`docs/TEST_REPORT.md` also has an updated working-tree copy with this audit's corrected size/test details, but it was not included in the isolated fix commit because that file already contained substantial uncommitted redesign edits. Other modified/untracked files in the Git status are existing redesign work and were preserved; they are not represented as newly authored by this audit.

## Commands to reproduce locally (Windows PowerShell)

From `D:\optimization\DataAnalysing`:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m playstore_intelligence.pipeline --dataset-dir dataset --output-dir data/processed
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\streamlit.exe run app.py
```

PowerShell activation is unnecessary; invoke venv executables directly. If PowerShell execution policy prevents running a script, do not modify that policy. For manual Kaggle downloads, set `PLAYSTORE_DATA_DIR` to the directory containing the official app catalog CSV.

## Remaining limitations and release actions

- The Git worktree was dirty at audit start and remains dirty; review and commit the full redesign changes separately. This audit did not rewrite history or bundle those edits into its fix commit.
- No Git remote, GitHub Actions execution, or live deployment exists; deployment is **not verified/not deployed**.
- Browser-based layout, responsive behavior, and actual download clicks are unverified; Streamlit AppTest and HTTP checks are not visual substitutes.
- Install strings are lower-bound bands. Summed lower bounds and HHI are approximate and must not be called exact market shares.
- Opportunity scores use category-relative min-max scaling and judgmental weights; demand and gap share install data. Rankings are not stable predictors and do not establish unmet demand.
- Ratings are selective and do not represent retention, feature satisfaction, or willingness to pay. Sample safeguards only require five rated listings; uncertainty intervals are not calculated.
- Product concepts are manually written hypotheses selected by ranked category, not algorithmically inferred solutions. Validate via interviews, competitor research, and prototype tests.
- Dataset bundle `license.txt` says CC BY 3.0 Unported; this conflicts with the brief's CC BY-SA 4.0 assertion. Verify current Kaggle terms before redistribution.
- Python 3.14.8 local checks passed. CI targets Python 3.13 and has not run on GitHub.

## GitHub and deployment follow-up

Checked again on 2026-10-23 for the GitHub release request:

- The user-provided URL was verified as the public repository `https://github.com/akhil-Mohammedd/playstore-intelligence`; GitHub reported it empty before the initial push. `origin` now points there, branch `master` is published, and remote/local SHA matched at `65f6f35188f7cfa4207014c44a6b03254017a8df` before the workflow update.
- `gh` (GitHub CLI) is not installed, but the normal HTTPS push succeeded through the configured Git Credential Manager. No force-push or history replacement was used.
- The redesign and deployment-readiness edits were present as uncommitted work at the start of this follow-up. After review and revalidation, they were included in commit `615e7a1 Prepare project for hosted release` and pushed to `origin/master`; no files were discarded.
- The app now checks an explicit data directory, `data/raw/`, and KaggleHub cache before attempting `kagglehub.dataset_download` for the public dataset. The KaggleHub call and actionable failure path have mocked unit tests. A fresh-host real outbound download has **not** been verified.
- Raw CSV is approximately 1.36 MB locally and remains ignored by Git. The bundled `dataset/license.txt` states CC BY 3.0 Unported; the Kaggle page could not be textually verified, and the project brief's CC BY-SA 4.0 statement conflicts. The raw CSV was not added to Git.
- Local result after the fallback change: 15 tests passed; Ruff lint and formatting passed; `pip check` passed; all five workspace-data AppTest pages rendered, and a changed demand weight changed scores. The existing server health/root URLs returned HTTP 200. These checks do not verify hosted network access or a public deployment.
- GitHub Actions run `39903535968` completed successfully on commit `048f9e1` (https://github.com/akhil-Mohammedd/playstore-intelligence/actions/runs/39903535968). The updated checkout v5/setup-python v6 workflow passed install, pip consistency, lint, format, and tests. No Streamlit Community Cloud app or live URL is configured. Deployment status: **not deployed**.

### Required next actions

1. Create the Community Cloud app from the verified repository using branch `master`, entry point `app.py`, and root `requirements.txt`. No secret is expected for the public dataset; outbound access to KaggleHub is required for an empty cache. If the host blocks it, configure `PLAYSTORE_DATA_DIR` to a permitted hosted file source rather than committing data before licence confirmation.
2. Verify the resulting public URL, all pages, weight-driven ranking changes, and CSV/Markdown download interactions. Add the live URL to the README only after these checks pass.

# Verification report

Execution date: 2026-10-23 (UTC environment clock). All Python commands used `.venv/Scripts/python.exe`.

| Check | Command/procedure | Actual result | Status |
|---|---|---|---|
| Dependency imports | Import pandas, NumPy, Plotly, Streamlit, KaggleHub from `.venv` | pandas 2.3.3, numpy 2.5.4, plotly 7.1.0, streamlit 1.66.1, kagglehub 1.0.3 import | Pass |
| Dependency consistency | `.venv/Scripts/python.exe -m pip check` | No broken requirements found | Pass |
| Unit/dashboard tests | `.venv/Scripts/python.exe -m pytest -q` | 7 passed; includes synthetic cleaners, parsing, category metrics, scoring, malformed row/duplicate eligibility, and Streamlit AppTest | Pass |
| Lint | `.venv/Scripts/python.exe -m ruff check .` | All checks passed | Pass |
| Format | `.venv/Scripts/python.exe -m ruff format --check .` | 20 files already formatted | Pass |
| Real dataset pipeline | `run_pipeline(output_dir=Path('data/processed'))` after KaggleHub download | Wrote cleaned CSV and quality JSON; source app CSV: 10,841 rows/13 columns; review CSV: 64,295 rows/5 columns | Pass |
| Streamlit AppTest | `AppTest.from_file('app.py').run()` | Dashboard title and KPIs rendered; zero AppTest exceptions | Pass |
| Streamlit HTTP smoke | Start `streamlit run app.py --server.headless true --server.port 8765`; GET `http://127.0.0.1:8765/_stcore/health` | HTTP 200, `ok`; local process terminated after check | Pass |
| CI workflow parse | PyYAML `safe_load` of `.github/workflows/ci.yml` | YAML parsed and contains `test` job | Pass (syntax parse only) |
| Editor type diagnostics | Zed language-server diagnostics after configuring `src` in `pyrightconfig.json` | Imports resolve; remaining diagnostics include unresolved Pandas/Plotly stubs and inferred DataFrame API types. No separate type-check command is configured | Not verified |
| Git ignore/repository review | `git init`; `git check-ignore -v ...`; staged-path review; `git diff --cached --check` | `.venv`, the local `dataset/` directory, processed outputs, and caches are ignored; staged list contains 25 code/docs/config files only; whitespace check clean | Pass |
| Credential-like literal scan | `git grep` over staged source | No matching credential-like literals found | Pass |
| GitHub Actions run | Requires push/PR to GitHub | No remote configured and no workflow run available | Not verified |
| Live deployment | No deployment configured | No live URL exists | Not deployed |

## Actual data-quality findings

The downloaded bundle contains app metadata and review CSVs plus `license.txt`. App metadata has 10,841 raw rows and 13 source columns. The pipeline measured 483 exact duplicate rows, 1,979 rows sharing an app name, one malformed category row (column-shifted source record), 1,475 missing/invalid ratings, one invalid install value, and one invalid update date. Exact duplicates and malformed category rows remain in the processed output but are excluded from analysis: 10,357 eligible records across 33 categories. Duplicate names are not used as a deletion rule.

## Actual scoring results

Default top five categories: Education, Shopping, Weather, Photography, Social. Under equal-weight and demand-light alternatives, the same five categories remain but Social and Photography exchange positions. This is limited rank sensitivity evidence, not a probability or prediction of product success. All five concept briefs are hypotheses requiring user research.

## Environment note

PowerShell script activation is blocked by the machine's existing execution policy. No policy was changed; commands invoked the venv interpreter directly as requested. A Windows Application Control policy blocked a native extension from the initial Pandas 3.1.0 wheel. Pandas 2.3.3 plus its timezone dependency imports successfully; security controls were not modified.

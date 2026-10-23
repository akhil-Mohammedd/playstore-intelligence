# PlayStore Intelligence

Decision-support dashboard for historical Google Play Store catalog analysis and app-opportunity research. The project distinguishes observed catalog metrics, calculated indicators, and hypotheses; it does not claim current trends or predict commercial success.

## Data source
[Kaggle: Google Play Store Apps](https://www.kaggle.com/datasets/lava18/google-play-store-apps), dataset identifier `lava18/google-play-store-apps`, by lava18. The downloaded bundle’s `license.txt` says Creative Commons Attribution 3.0 Unported (CC BY 3.0). This conflicts with the CC BY-SA 4.0 attribution in the project brief; the Kaggle listing was not textually verifiable during this run. Preserve the source notice and attribution, and confirm the current dataset-page licence before redistributing data or adaptations. Raw files are kept in KaggleHub's user cache and excluded from Git. Retrieval time is recorded by the pipeline; it is not an observation collection date.

## Setup (Windows PowerShell)

```powershell
cd D:\optimization\DataAnalysing
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

PowerShell activation may be restricted by the machine's execution policy. Activation is optional; use the explicit `.venv\Scripts\` executables below to avoid changing that policy.

Download through KaggleHub using your local Kaggle authentication:

```powershell
.\.venv\Scripts\python.exe -c "import kagglehub; print(kagglehub.dataset_download('lava18/google-play-store-apps'))"
```

Alternatively download the dataset from the official Kaggle page in a browser and put the app catalog CSV (and optionally reviews CSV) under `data/raw/`, or set `$env:PLAYSTORE_DATA_DIR = 'D:\path\to\downloaded\folder'` before starting Streamlit. Do not commit credentials or raw data. KaggleHub can use the existing local credential setup; follow Kaggle's official API-token instructions if prompted. Never paste a token into chat.

For a fresh hosted instance, the app first checks `PLAYSTORE_DATA_DIR`, `data/raw/`, and the KaggleHub cache. If none has the app catalog, it attempts to download this public dataset with KaggleHub into its cache; this avoids committing the raw CSV and does not intentionally require a private Kaggle token. Hosted startup therefore depends on outbound network access to Kaggle and can be slower on a cold start. If that download is blocked, the page displays an actionable error and the host must provide the official CSV through `PLAYSTORE_DATA_DIR`. This behavior is locally unit-tested with a mocked downloader; hosted network access is not yet verified.

Run the quality/cleaning pipeline from the repository root (uses the latest KaggleHub cache by default):

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m playstore_intelligence.pipeline
```

For a manually downloaded CSV folder, pass `--dataset-dir`; to download through KaggleHub and process in one step, use `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m playstore_intelligence.pipeline --download`.

Launch dashboard:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Run automated checks:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
```

## Dashboard
The five-step navigation is Market Overview → Explore Categories → Competition & Gaps → Opportunity Finder → Build Plan. Category filters update summaries, profiles, charts, and CSV exports. Opportunity weights update component contributions, scores, explanations, and ranks live; reset restores the documented defaults. Plans export as Markdown. Methodology and cleaning rules are available below the Overview metrics.

## Architecture
`src/playstore_intelligence/` contains data discovery/loading, cleaning, descriptive analytics, scoring, recommendations, and pipeline modules. `app.py` is a thin Streamlit UI; tests use small synthetic fixtures and do not substitute for real-data validation.

## Method and limitations
Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md). Ratings and installs are observational and do not establish causality. Category total installs are shown alongside median per-app install lower bounds. The score is not trained or commercially validated: active weights are normalized, missing empirical components use a visible neutral 0.50 fallback, feasibility is a fixed neutral engineering assumption, and evidence coverage reports the weighted availability of empirical features. Concepts require primary user research and demand validation.

## Verified snapshot findings
The KaggleHub version 6 app CSV contains 10,841 source rows and 13 columns. The quality pipeline identified 483 exact duplicate rows, 1,979 rows with repeated app names (not necessarily duplicates), 1 column-shifted invalid-category record, 1,475 missing/invalid ratings, and one malformed install/date value each. It retained rows for audit and excluded exact duplicates plus the invalid-category record from category analysis, leaving 10,357 analysis-eligible rows across 33 categories. These are calculated findings from the downloaded snapshot, not current-market statistics.

Under default heuristic weights, the leading categories are Education, Shopping, Weather, Photography, and Social. Alternative weight scenarios retain the same five but swap Social and Photography within the top five. Rankings only weakly stable at this close boundary; they are not app-success forecasts. The score uses category-relative features and neutral feasibility. See the quality JSON and test report for run-specific detail.

## Deployment status
Repository: [akhil-Mohammedd/playstore-intelligence](https://github.com/akhil-Mohammedd/playstore-intelligence) (public; default branch `master`). The release commit has been pushed and GitHub Actions has passed. The app is **not deployed** and no live dashboard URL exists. For Streamlit Community Cloud, create an app from this repository, branch `master`, entry point `app.py`, and root `requirements.txt`. Select a supported Python version and verify the dependency build; CI uses Python 3.13 while local development uses 3.14.8. No app secrets are expected for the public Kaggle dataset. On a cold host, app startup attempts KaggleHub download and therefore needs outbound network access. If unavailable, configure `PLAYSTORE_DATA_DIR` to a permitted data source; do not commit the raw CSV until the dataset licence and redistribution terms are confirmed.

## Verification state
Actual dataset pipeline, tests, linting, and dashboard AppTest have been executed. The deployment fallback is covered by mocked unit tests, but hosted Kaggle access and a live deployment are not verified. GitHub Actions passed on commit `65f6f35`; the workflow action-version update is awaiting its own run. See [docs/TEST_REPORT.md](docs/TEST_REPORT.md) and [docs/RELEASE_AUDIT.md](docs/RELEASE_AUDIT.md) for command-level results and release status.

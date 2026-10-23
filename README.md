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
python -c "import kagglehub; print(kagglehub.dataset_download('lava18/google-play-store-apps'))"
```

Alternatively download the dataset from the official Kaggle page in a browser and put the app catalog CSV (and optionally reviews CSV) under `data/raw/`. Do not commit credentials or raw data. KaggleHub can use the existing local credential setup; follow Kaggle's official API-token instructions if prompted. Never paste a token into chat.

Run the quality/cleaning pipeline from the repository root (uses the latest KaggleHub cache by default):

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m playstore_intelligence.pipeline
```

For a manually downloaded CSV folder, pass `--dataset-dir`; to download through KaggleHub and process in one step, use `python -m playstore_intelligence.pipeline --download`.

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
Sections include Overview, Category Explorer, Competition Analysis, Opportunity Finder, App Explorer, and Methodology. Install bands are retained as source text and separately parsed as lower bounds. Opportunity ranks are heuristic category-level investigation prompts; configurable weights and alternative scenarios make ranking sensitivity visible.

## Architecture
`src/playstore_intelligence/` contains data discovery/loading, cleaning, descriptive analytics, scoring, recommendations, and pipeline modules. `app.py` is a thin Streamlit UI; tests use small synthetic fixtures and do not substitute for real-data validation.

## Method and limitations
Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md). Ratings and installs are observational and do not establish causality. Category total installs are shown alongside median per-app install lower bounds. The score is not trained or commercially validated. Concepts require primary user research and demand validation.

## Verified snapshot findings
The KaggleHub version 6 app CSV contains 10,841 source rows and 13 columns. The quality pipeline identified 483 exact duplicate rows, 1,979 rows with repeated app names (not necessarily duplicates), 1 column-shifted invalid-category record, 1,475 missing/invalid ratings, and one malformed install/date value each. It retained rows for audit and excluded exact duplicates plus the invalid-category record from category analysis, leaving 10,357 analysis-eligible rows across 33 categories. These are calculated findings from the downloaded snapshot, not current-market statistics.

Under default heuristic weights, the leading categories are Education, Shopping, Weather, Photography, and Social. Alternative weight scenarios retain the same five but swap Social and Photography within the top five. Rankings only weakly stable at this close boundary; they are not app-success forecasts. The score uses category-relative features and neutral feasibility. See the quality JSON and test report for run-specific detail.

## Verification state
Actual dataset pipeline, tests, linting, and dashboard AppTest have been executed. This project does not claim deployment or public GitHub publication. See [docs/TEST_REPORT.md](docs/TEST_REPORT.md) for command-level results.

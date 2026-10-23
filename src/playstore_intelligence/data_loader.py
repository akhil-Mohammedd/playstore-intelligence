"""Dataset discovery and loading."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATASET_ID = "lava18/google-play-store-apps"

APP_COLUMNS = {
    "App",
    "Category",
    "Rating",
    "Reviews",
    "Size",
    "Installs",
    "Type",
    "Price",
    "Content Rating",
    "Genres",
    "Last Updated",
}


def discover_csvs(root: Path) -> list[Path]:
    """Return CSV files below root, sorted deterministically."""
    if not root.exists():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    return sorted(root.rglob("*.csv"))


def find_app_csv(files: list[Path]) -> Path:
    """Find the app metadata CSV by required source columns."""
    for path in files:
        try:
            columns = set(pd.read_csv(path, nrows=0).columns)
        except (OSError, pd.errors.ParserError, UnicodeError):
            continue
        if APP_COLUMNS.issubset(columns):
            return path
    raise FileNotFoundError(
        "No app metadata CSV with the expected Google Play columns was found."
    )


def load_app_data(path: Path) -> pd.DataFrame:
    """Load app metadata without altering the source file."""
    if not path.is_file():
        raise FileNotFoundError(f"App metadata CSV was not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError(f"Could not read app metadata CSV {path}: {exc}") from exc
    missing = APP_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(sorted(missing))}"
        )
    return frame


def download_public_dataset() -> Path:
    """Download the public Kaggle catalog into KaggleHub's cache."""
    try:
        import kagglehub

        return Path(kagglehub.dataset_download(DATASET_ID))
    except Exception as exc:
        raise RuntimeError(
            "The public Kaggle Play Store dataset is not available locally and "
            "KaggleHub could not download it. Check hosted outbound network access, "
            "or provide the official app catalog CSV through PLAYSTORE_DATA_DIR."
        ) from exc


def find_dataset_dir(local_dir: Path | None = None) -> Path:
    """Use an explicit local folder, otherwise the standard KaggleHub cache."""
    if local_dir:
        if not local_dir.exists():
            raise FileNotFoundError(
                f"Configured local dataset directory does not exist: {local_dir}"
            )
        return local_dir
    import os
    from pathlib import Path as _Path

    cache = Path(
        os.environ.get("KAGGLEHUB_CACHE", _Path.home() / ".cache" / "kagglehub")
    )
    candidates = sorted(
        (cache / "datasets" / "lava18" / "google-play-store-apps" / "versions").glob(
            "*"
        )
    )
    for candidate in reversed(candidates):
        if list(candidate.rglob("*.csv")):
            return candidate
    raise FileNotFoundError(
        "Kaggle dataset is not cached. Run `python -m playstore_intelligence.pipeline --download` with `PYTHONPATH=src`, or set PLAYSTORE_DATA_DIR to a folder containing the CSV."
    )

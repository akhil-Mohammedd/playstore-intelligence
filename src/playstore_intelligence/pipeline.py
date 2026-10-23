"""End-to-end reproducible dataset processing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .cleaning import clean_apps
from .data_loader import discover_csvs, find_app_csv, find_dataset_dir, load_app_data


def run_pipeline(
    dataset_dir: Path | None = None, output_dir: Path = Path("data/processed")
) -> tuple[Path, Path]:
    source_dir = find_dataset_dir(dataset_dir)
    source = find_app_csv(discover_csvs(source_dir))
    raw = load_app_data(source)
    cleaned, quality = clean_apps(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path, report_path = (
        output_dir / "apps_cleaned.csv",
        output_dir / "data_quality.json",
    )
    cleaned.to_csv(csv_path, index=False)
    dataset_files = []
    for path in sorted(source_dir.iterdir()):
        if path.is_file():
            entry = {"name": path.name, "bytes": path.stat().st_size}
            if path.suffix.lower() == ".csv":
                table = raw if path == source else pd.read_csv(path)
                entry["rows"] = len(table)
                entry["columns"] = list(table.columns)
            dataset_files.append(entry)
    report = {
        "source_url": "https://www.kaggle.com/datasets/lava18/google-play-store-apps",
        "dataset_id": "lava18/google-play-store-apps",
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "source_file": source.name,
        "source_directory": str(source_dir),
        "source_columns": list(raw.columns),
        "available_dataset_files": dataset_files,
        **quality,
    }
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return csv_path, report_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Download (optional) and process Play Store app metadata."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the public dataset with KaggleHub first",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        help="Use a local directory containing source CSV files",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    dataset_dir = args.dataset_dir
    if args.download:
        import kagglehub

        dataset_dir = Path(kagglehub.dataset_download("lava18/google-play-store-apps"))
    csv_path, report_path = run_pipeline(dataset_dir, args.output_dir)
    print(f"Cleaned data: {csv_path}\nQuality report: {report_path}")


if __name__ == "__main__":
    main()

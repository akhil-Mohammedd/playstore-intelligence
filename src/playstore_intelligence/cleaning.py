"""Auditable type parsing and normalization for source app records."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


def _number(value: Any) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "null", "none", "n/a"}:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def parse_installs(value: Any) -> float:
    """Parse install band lower bound; retain raw Install band in output."""
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().replace(",", "")
    if text in {"", "0"}:
        return 0.0
    if not re.fullmatch(r"\d+(?:\.\d+)?\+?", text):
        return float("nan")
    return float(text.rstrip("+"))


def parse_size_mb(value: Any) -> float:
    """Convert common Play Store size units to MB; invalid sizes stay missing."""
    if pd.isna(value):
        return float("nan")
    text = str(value).strip()
    match = re.fullmatch(
        r"((?:\d+(?:\.\d*)?|\.\d+))\s*(GB|MB|KB|B|G|M|K)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return float("nan")
    amount, unit = float(match.group(1)), match.group(2).upper()
    return {
        "GB": amount * 1024,
        "G": amount * 1024,
        "MB": amount,
        "M": amount,
        "KB": amount / 1024,
        "K": amount / 1024,
        "B": amount / (1024 * 1024),
    }[unit]


def clean_apps(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return a cleaned analytical frame and data-quality summary.

    Duplicate app names are reported, never deduplicated: names can refer to
    separate products or versions and source rows are retained for audit.
    """
    expected = {
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
    missing = expected.difference(raw.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {', '.join(sorted(missing))}")
    df = raw.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        df[col] = df[col].replace({"": pd.NA, "NaN": pd.NA, "nan": pd.NA})
    df["rating_raw"] = df["rating"]
    df["reviews_raw"] = df["reviews"]
    df["installs_raw"] = df["installs"]
    df["price_raw"] = df["price"]
    df["size_raw"] = df["size"]
    df["last_updated_raw"] = df["last_updated"]
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df.loc[~df["rating"].between(1, 5), "rating"] = float("nan")
    df["reviews"] = df["reviews"].map(_number)
    df.loc[df["reviews"] < 0, "reviews"] = float("nan")
    df["estimated_installs_lower_bound"] = df["installs"].map(parse_installs)
    df["price_usd"] = df["price"].map(
        lambda x: _number(re.sub(r"[^\d.,-]", "", str(x)) if pd.notna(x) else x)
    )
    df.loc[df["price_usd"] < 0, "price_usd"] = float("nan")
    df["size_mb"] = df["size"].map(parse_size_mb)
    df["last_updated"] = pd.to_datetime(
        df["last_updated"], format="mixed", errors="coerce"
    )
    df["type"] = df["type"].str.casefold().replace({"free": "Free", "paid": "Paid"})
    df["category_valid"] = df["category"].str.fullmatch(r"[A-Z_]+", na=False)
    df["exact_duplicate"] = raw.duplicated(keep="first")
    df["analysis_eligible"] = df["category_valid"] & ~df["exact_duplicate"]
    quality = {
        "raw_rows": len(raw),
        "exact_duplicate_rows": int(raw.duplicated().sum()),
        "invalid_category_rows": int((~df["category_valid"]).sum()),
        "analysis_eligible_rows": int(df["analysis_eligible"].sum()),
        "duplicate_app_names": int(df["app"].duplicated(keep=False).sum()),
        "missing_percent_by_column": (raw.isna().mean().mul(100).round(2).to_dict()),
        "invalid_rating_rows": int(
            (
                pd.to_numeric(raw["Rating"], errors="coerce").notna()
                & ~pd.to_numeric(raw["Rating"], errors="coerce").between(1, 5)
            ).sum()
            + (
                raw["Rating"].notna()
                & pd.to_numeric(raw["Rating"], errors="coerce").isna()
            ).sum()
        ),
        "missing_or_invalid_rating_rows": int(df["rating"].isna().sum()),
        "invalid_install_rows": int(
            (
                df["estimated_installs_lower_bound"].isna() & raw["Installs"].notna()
            ).sum()
        ),
        "invalid_review_rows": int(
            (df["reviews"].isna() & raw["Reviews"].notna()).sum()
        ),
        "invalid_price_rows": int(
            (df["price_usd"].isna() & raw["Price"].notna()).sum()
        ),
        "unparseable_size_rows": int(
            (
                df["size_mb"].isna()
                & raw["Size"].notna()
                & ~raw["Size"].astype(str).str.casefold().eq("varies with device")
            ).sum()
        ),
        "invalid_date_rows": int(
            (df["last_updated"].isna() & raw["Last Updated"].notna()).sum()
        ),
        "cleaned_rows": len(df),
    }
    return df, quality

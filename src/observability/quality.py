from __future__ import annotations

from typing import Any
from pathlib import Path
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    total_rows = len(df)
    
    # Check paper_id and title
    if total_rows > 0:
        paper_id_nulls = int(df["paper_id"].isna().sum() + (df["paper_id"].str.strip() == "").sum())
        paper_id_unique = bool(df["paper_id"].is_unique)
        title_nulls = int(df["title"].isna().sum() + (df["title"].str.strip() == "").sum())
        
        # Summary length check (warn if abstract is under 50 chars)
        summary_too_short = int((df["summary"].fillna("").str.len() < 50).sum())
        min_summary_len = int(df["summary"].fillna("").str.len().min())
        max_summary_len = int(df["summary"].fillna("").str.len().max())
        mean_summary_len = float(df["summary"].fillna("").str.len().mean())
        
        # Freshness check
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    else:
        paper_id_nulls = 0
        paper_id_unique = True
        title_nulls = 0
        summary_too_short = 0
        min_summary_len = 0
        max_summary_len = 0
        mean_summary_len = 0.0
        stale_rows = 0
        
    passed_nulls_check = bool(paper_id_nulls == 0 and title_nulls == 0)
    passed_uniqueness_check = bool(paper_id_unique)
    passed_summary_check = bool(summary_too_short == 0)
    passed_freshness_check = bool(stale_rows == 0)
    
    success = bool(passed_nulls_check and passed_uniqueness_check and passed_summary_check and passed_freshness_check)
    
    report = {
        "report_name": report_name,
        "success": success,
        "total_rows": total_rows,
        "checks": {
            "null_values": {
                "paper_id_null_count": paper_id_nulls,
                "title_null_count": title_nulls,
                "success": passed_nulls_check
            },
            "uniqueness": {
                "paper_id_unique": paper_id_unique,
                "success": passed_uniqueness_check
            },
            "summary_length": {
                "summary_too_short_count": summary_too_short,
                "min_length": min_summary_len,
                "max_length": max_summary_len,
                "mean_length": mean_summary_len,
                "success": passed_summary_check
            },
            "freshness": {
                "stale_row_count": stale_rows,
                "freshness_threshold_days": settings.freshness_threshold_days,
                "success": passed_freshness_check
            }
        }
    }
    
    # Save the report
    report_dir = settings.paths.quality_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{report_name}.json"
    write_json(report_path, report)
    
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    total_rows = len(df)
    if total_rows > 0:
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    else:
        latest_published = "N/A"
        oldest_published = "N/A"
        stale_rows = 0
        
    is_fresh = bool(stale_rows == 0 and total_rows > 0)
    
    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": is_fresh,
        "freshness_threshold_days": settings.freshness_threshold_days
    }
    
    if report_path:
        out = Path(report_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_json(out, report)
        
    return report

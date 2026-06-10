from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace, compact_join


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories",
            "primary_category", "published", "updated", "abs_url", "pdf_url", "comment",
            "authors_joined", "categories_joined", "summary_chars", "text_for_embedding", "age_days"
        ])

    data = []
    for r in records:
        data.append({
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        })
    df = pd.DataFrame(data)

    # 1. Normalize fields
    df["title"] = df["title"].apply(lambda x: normalize_whitespace(x) if isinstance(x, str) else "")
    df["summary"] = df["summary"].apply(lambda x: normalize_whitespace(x) if isinstance(x, str) else "")

    # 2. Join list columns
    df["authors_joined"] = df["authors"].apply(lambda x: compact_join(x) if isinstance(x, list) else "")
    df["categories_joined"] = df["categories"].apply(lambda x: compact_join(x) if isinstance(x, list) else "")

    # 3. Create lengths & text_for_embedding
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = (
        "Title: " + df["title"] + "\n"
        "Authors: " + df["authors_joined"] + "\n"
        "Summary: " + df["summary"]
    )

    # 4. Parse dates and calculate age_days
    run_date_naive = run_date.replace(tzinfo=None)
    published_dt = pd.to_datetime(df["published"], errors="coerce")
    published_dt = published_dt.fillna(run_date_naive)
    
    # Calculate age_days
    df["age_days"] = (run_date_naive - published_dt.dt.tz_localize(None)).dt.days
    df["age_days"] = df["age_days"].fillna(0).astype(int)

    # Save dates back as YYYY-MM-DD strings
    df["published"] = published_dt.dt.strftime("%Y-%m-%d")
    
    updated_dt = pd.to_datetime(df["updated"], errors="coerce")
    updated_dt = updated_dt.fillna(published_dt)
    df["updated"] = updated_dt.dt.strftime("%Y-%m-%d")

    # 5. Drop duplicates and filter out bad rows
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["paper_id"].notna() & (df["paper_id"].str.strip() != "")]
    df = df[df["title"].notna() & (df["title"].str.strip() != "")]
    df = df[df["summary"].notna() & (df["summary"].str.strip() != "")]

    # 6. Sort and return
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    
    return df


if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add src directory to PYTHONPATH automatically if running directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    from core.config import load_settings
    from core.utils import now_utc, write_csv, ensure_parent
    from ingestion.crossref import load_raw_records
    
    print("Loading settings...")
    settings = load_settings()
    
    raw_path = settings.paths.raw_records_json
    print(f"Loading raw records from: {raw_path}")
    if not raw_path.exists():
        print(f"Error: Raw records file does not exist at {raw_path}. Run crossref.py first.", file=sys.stderr)
        sys.exit(1)
        
    records = load_raw_records(raw_path)
    print(f"Loaded {len(records)} raw records.")
    
    print("Cleaning records...")
    df = build_clean_dataframe(records, now_utc())
    print(f"Cleaning complete. Cleaned dataframe has {len(df)} rows.")
    
    csv_path = settings.paths.clean_csv
    json_path = settings.paths.clean_json
    
    print(f"Saving cleaned CSV to: {csv_path}")
    write_csv(df, csv_path)
    
    print(f"Saving cleaned JSON to: {json_path}")
    ensure_parent(json_path)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    
    print("\nSample cleaned data:")
    if not df.empty:
        print(df[["paper_id", "title", "published", "age_days"]].head(2))

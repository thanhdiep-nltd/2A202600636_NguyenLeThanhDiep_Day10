from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    corrupted_df = df.copy()
    
    log = {
        "original_rows": len(df),
        "dropped_latest": 0,
        "blanked_summaries": 0,
        "injected_noise": 0,
        "truncated_titles": 0,
        "stale_dates": 0,
        "duplicates_added": 0
    }
    
    # 1. Drop mot so latest records (the first 3 rows in published descending order)
    if len(corrupted_df) >= 5:
        corrupted_df = corrupted_df.iloc[3:].reset_index(drop=True)
        log["dropped_latest"] = 3
        
    # 2. Blank summary o mot so dong
    if len(corrupted_df) > 0:
        corrupted_df.loc[0, "summary"] = ""
        log["blanked_summaries"] += 1
    if len(corrupted_df) > 1:
        corrupted_df.loc[1, "summary"] = ""
        log["blanked_summaries"] += 1
        
    # 3. Inject noise vao text (summary)
    noise_str = " [NOISE_CORRUPTION_SYSTEM_ERROR_CORRUPTED_TEXT_12345] "
    if len(corrupted_df) > 2:
        corrupted_df.loc[2, "summary"] = str(corrupted_df.loc[2, "summary"]) + noise_str
        log["injected_noise"] += 1
    if len(corrupted_df) > 3:
        corrupted_df.loc[3, "summary"] = str(corrupted_df.loc[3, "summary"]) + noise_str
        log["injected_noise"] += 1
        
    # 4. Lam title bi truncate
    if len(corrupted_df) > 4:
        corrupted_df.loc[4, "title"] = corrupted_df.loc[4, "title"][:15]
        log["truncated_titles"] += 1
    if len(corrupted_df) > 5:
        corrupted_df.loc[5, "title"] = corrupted_df.loc[5, "title"][:15]
        log["truncated_titles"] += 1
        
    # 5. Lam published date cu di (make it stale)
    if len(corrupted_df) > 6:
        corrupted_df.loc[6, "published"] = "2010-01-01"
        corrupted_df.loc[6, "age_days"] = 6000
        log["stale_dates"] += 1
    if len(corrupted_df) > 7:
        corrupted_df.loc[7, "published"] = "2010-01-01"
        corrupted_df.loc[7, "age_days"] = 6000
        log["stale_dates"] += 1
        
    # 6. Add duplicate rows
    if len(corrupted_df) > 0:
        last_row = corrupted_df.iloc[[-1]]
        corrupted_df = pd.concat([corrupted_df, last_row, last_row], ignore_index=True)
        log["duplicates_added"] = 2
        
    # 7. Rebuild text_for_embedding
    corrupted_df["text_for_embedding"] = (
        "Title: " + corrupted_df["title"].fillna("") + "\n"
        "Authors: " + corrupted_df["authors_joined"].fillna("") + "\n"
        "Summary: " + corrupted_df["summary"].fillna("")
    )
    
    log["final_rows"] = len(corrupted_df)
    
    # 8. Ghi corruption log vao output_log_path
    if output_log_path:
        out = Path(output_log_path)
        write_json(out, log)
        
    return corrupted_df

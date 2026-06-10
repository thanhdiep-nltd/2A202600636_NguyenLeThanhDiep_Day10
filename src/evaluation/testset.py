from __future__ import annotations

from typing import Any
from pathlib import Path
import pandas as pd

from core.utils import ensure_parent, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    # 1. Kiem tra so luong document toi thieu.
    if len(df) < 3:
        raise ValueError(f"Not enough documents to build a test set. Expected at least 3, got {len(df)}")

    # 2. Chon mot so paper dai dien (lay tối đa 10 papers đầu tiên).
    sample_size = min(10, len(df))
    sample_df = df.head(sample_size)

    test_set = []
    sample_id_counter = 0

    # 3. Tao nhieu loai cau hoi:
    for _, row in sample_df.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row["summary"]
        authors = row["authors_joined"]
        published = row["published"]
        categories = row["categories_joined"] if "categories_joined" in row and pd.notna(row["categories_joined"]) else row.get("primary_category", "unknown")

        # summary type question
        sample_id_counter += 1
        test_set.append({
            "id": f"q_{sample_id_counter}",
            "question_type": "summary",
            "question": f"What is the summary of the paper titled '{title}'?",
            "ground_truth": summary,
            "ground_truth_doc_ids": [paper_id]
        })

        # authors type question
        if pd.notna(authors) and str(authors).strip():
            sample_id_counter += 1
            test_set.append({
                "id": f"q_{sample_id_counter}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper titled '{title}'?",
                "ground_truth": str(authors),
                "ground_truth_doc_ids": [paper_id]
            })

        # date type question
        if pd.notna(published) and str(published).strip():
            sample_id_counter += 1
            test_set.append({
                "id": f"q_{sample_id_counter}",
                "question_type": "date",
                "question": f"When was the paper titled '{title}' published?",
                "ground_truth": str(published),
                "ground_truth_doc_ids": [paper_id]
            })

        # categories type question
        if pd.notna(categories) and str(categories).strip():
            sample_id_counter += 1
            test_set.append({
                "id": f"q_{sample_id_counter}",
                "question_type": "categories",
                "question": f"What are the categories or subjects of the paper titled '{title}'?",
                "ground_truth": str(categories),
                "ground_truth_doc_ids": [paper_id]
            })

    # 5. Ghi file JSON vao output_path.
    if output_path:
        out = Path(output_path)
        write_json(out, test_set)

    return test_set


if __name__ == "__main__":
    import sys
    # Add src directory to PYTHONPATH automatically if running directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
    from core.config import load_settings
    
    print("Loading settings...")
    settings = load_settings()
    
    clean_path = settings.paths.clean_csv
    print(f"Loading cleaned papers from: {clean_path}")
    if not clean_path.exists():
        print(f"Error: Cleaned papers file does not exist at {clean_path}. Run cleaning.py first.", file=sys.stderr)
        sys.exit(1)
        
    df = pd.read_csv(clean_path)
    print(f"Loaded {len(df)} papers.")
    
    output_path = settings.paths.eval_testset
    print(f"Building test set at: {output_path}")
    test_set = build_test_set(df, output_path)
    print(f"Successfully generated {len(test_set)} questions in test set.")
    
    if test_set:
        print("\nSample question:")
        print(test_set[0])

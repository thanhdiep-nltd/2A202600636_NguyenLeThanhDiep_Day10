from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, now_utc, ensure_parent
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow.

    Pseudo-code:
    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate.
    5. Run quality checks/freshness tren corrupted data.
    6. Repair lai tu raw records.
    7. Evaluate repaired dataset.
    8. Tao comparison report.
    """
    # 1. Load settings, baseline metrics, and clean dataset
    print("Step 1: Loading settings and baseline metrics...")
    settings = load_settings()
    
    try:
        baseline_metrics = read_json(settings.paths.baseline_metrics)
    except Exception as e:
        print(f"Error loading baseline metrics: {e}. Make sure to run phase1 first.")
        return
        
    try:
        clean_df = pd.read_csv(settings.paths.clean_csv)
    except Exception as e:
        print(f"Error loading clean papers: {e}. Make sure to run phase1 first.")
        return
        
    # 2. Tao corrupted dataframe
    print("\nStep 2: Simulating data corruption on clean dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"Corrupted dataset has {len(corrupted_df)} rows.")

    # 3. Save corrupted artifacts
    print("\nStep 3: Saving corrupted dataset artifacts...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    print(f"Saved corrupted CSV to: {settings.paths.corrupted_clean_csv}")
    ensure_parent(settings.paths.corrupted_clean_json)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"Saved corrupted JSON to: {settings.paths.corrupted_clean_json}")

    # 4. Rebuild index va evaluate (corrupted)
    print("\nStep 4: Rebuilding embedding index and evaluating corrupted pipeline...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, 
        settings, 
        settings.paths.corrupted_embeddings_json
    )
    
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers
    )
    print("Corrupted evaluation completed.")
    print("Corrupted QA Metrics:")
    for k, v in corrupted_bundle.summary.items():
        if k != "ragas":
            print(f"  {k}: {v}")

    # 5. Run quality checks/freshness tren corrupted data
    print("\nStep 5: Running quality and freshness checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, 
        settings, 
        settings.paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(f"Corrupted quality checks success: {corrupted_quality['success']}")
    print(f"Corrupted data is fresh: {corrupted_freshness['is_fresh']}")

    # 6. Repair lai tu raw records
    print("\nStep 6: Repairing dataset from raw source records...")
    raw_records_path = settings.paths.raw_records_json
    if not raw_records_path.exists():
        print(f"Error: Raw records file not found at {raw_records_path}.")
        return
    raw_records = load_raw_records(raw_records_path)
    
    run_date = now_utc()
    repaired_df = build_clean_dataframe(raw_records, run_date)
    print(f"Repaired dataset has {len(repaired_df)} rows.")

    print("Saving repaired dataset artifacts...")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    print(f"Saved repaired CSV to: {settings.paths.repaired_clean_csv}")
    ensure_parent(settings.paths.repaired_clean_json)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"Saved repaired JSON to: {settings.paths.repaired_clean_json}")

    print("Rebuilding embedding index for repaired dataset...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, 
        settings, 
        settings.paths.repaired_embeddings_json
    )

    # 7. Evaluate repaired dataset
    print("\nStep 7: Evaluating repaired QA pipeline...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers
    )
    print("Repaired evaluation completed.")
    print("Repaired QA Metrics:")
    for k, v in repaired_bundle.summary.items():
        if k != "ragas":
            print(f"  {k}: {v}")

    print("Running quality and freshness checks on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, 
        settings, 
        settings.paths.quality_dir / "repaired_freshness_report.json"
    )
    print(f"Repaired quality checks success: {repaired_quality['success']}")
    print(f"Repaired data is fresh: {repaired_freshness['is_fresh']}")

    # 8. Tao comparison report
    print("\nStep 8: Generating corruption and recovery comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness
    )
    print(f"Comparison report generated at: {settings.paths.comparison_report}")


if __name__ == "__main__":
    main()

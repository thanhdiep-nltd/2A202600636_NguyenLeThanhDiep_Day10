from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, ensure_parent
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report


def main() -> None:
    """Xay dung baseline pipeline end-to-end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    # 1. Load settings
    print("Step 1: Loading settings...")
    settings = load_settings()
    
    # 2. Load hoac fetch raw records
    print("\nStep 2: Ingesting raw records...")
    raw_records_path = settings.paths.raw_records_json
    if not raw_records_path.exists() or settings.refresh_source:
        print("Fetching raw records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading raw records from cache: {raw_records_path}")
        records = load_raw_records(raw_records_path)
    print(f"Ingested {len(records)} raw records.")

    # 3. Clean data
    print("\nStep 3: Cleaning records...")
    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    print(f"Cleaned dataset has {len(df)} rows.")

    # 4. Save clean CSV/JSON
    print("\nStep 4: Saving cleaned records...")
    write_csv(df, settings.paths.clean_csv)
    print(f"Saved CSV to: {settings.paths.clean_csv}")
    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
    print(f"Saved JSON to: {settings.paths.clean_json}")

    # 5. Build Chroma index
    print("\nStep 5: Building ChromaDB index...")
    index = LocalEmbeddingIndex.build(df, settings)
    print("ChromaDB index build completed.")

    # 6. Tao hoac load evaluation set
    print("\nStep 6: Preparing evaluation test set...")
    test_set_path = settings.paths.eval_testset
    if not test_set_path.exists() or settings.refresh_test_set:
        print("Generating new evaluation test set...")
        build_test_set(df, test_set_path)
    else:
        print(f"Loading existing test set from: {test_set_path}")
    
    # 7. Evaluate
    print("\nStep 7: Evaluating QA pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=test_set_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers
    )
    print("Pipeline evaluation completed.")
    print("Baseline QA Metrics:")
    for k, v in bundle.summary.items():
        if k != "ragas":
            print(f"  {k}: {v}")

    # 8. Run quality checks va freshness report
    print("\nStep 8: Running quality and freshness checks...")
    quality_report = run_data_quality_checks(df, settings, "baseline_quality")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"Quality checks success: {quality_report['success']}")
    print(f"Data is fresh: {freshness_report['is_fresh']}")

    # 9. Tao markdown report
    print("\nStep 9: Generating markdown report...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "total_records": len(records)
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_report,
        freshness=freshness_report
    )
    print(f"Markdown baseline report created at: {settings.paths.baseline_report}")

    # 10. Co the demo agent tren vai sample question
    print("\nStep 10: Running QA agent demo...")
    try:
        from retrieval.agent import build_agent, run_agent_question
        agent = build_agent(settings, index)
        demo_q = "What is the primary topic of the corpus?"
        print(f"Demo Question: '{demo_q}'")
        ans = run_agent_question(agent, demo_q)
        print(f"Agent Answer:\n{ans}")
    except Exception as e:
        print(f"Agent demo skipped: {e}")


if __name__ == "__main__":
    main()

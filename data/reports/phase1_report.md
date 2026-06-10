# Baseline Data Pipeline & Observability Report

## 1. Source Summary
- **Source API:** Crossref REST API
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:2025-12-12,has-abstract:true`
- **Max Results:** 24
- **Total Records Fetched:** 24

## 2. Evaluation Metrics (QA Agent Baseline)
- **Total Test Samples:** 40
- **Retrieval Hit Rate:** 100.00%
- **Mean Token F1 Score:** 0.3096
- **Judge Accuracy (Accuracy):** 25.00%
- **Mean Judge Score (1-5):** 2.00/5.00

## 3. Data Quality Checks
- **Overall Quality Success:** ✅ PASSED
- **Total Clean Rows:** 23
- **Check Details:**
  - **Null Values Check:** ✅ PASSED (paper_id nulls: 0, title nulls: 0)
  - **Uniqueness Check:** ✅ PASSED (Unique paper_id: True)
  - **Summary Length Check:** ✅ PASSED (Short summaries: 0, Min/Max/Mean length: 1037/2506/1805.5)
  - **Freshness Check:** ✅ PASSED (Stale rows: 0)

## 4. Freshness Monitoring
- **Is Fresh:** ✅ YES
- **Latest Published Date:** 2026-06-02
- **Oldest Published Date:** 2025-12-19
- **Stale Rows (>180 days):** 0/23

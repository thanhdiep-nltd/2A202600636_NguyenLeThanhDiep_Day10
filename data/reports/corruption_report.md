# Data Corruption & Recovery Comparison Report

This report evaluates the impact of simulated data corruption on our RAG Agent's performance and details how well the pipeline recovers after data repair.

## 1. QA Agent Performance Comparison

| Metric | Baseline (Clean) | Corrupted | Repaired |
| :--- | :---: | :---: | :---: |
| **Total Samples** | 40 | 40 | 40 |
| **Retrieval Hit Rate** | 100.00% | 70.00% | 100.00% |
| **Mean Token F1** | 0.3096 | 0.1879 | 0.3096 |
| **Judge Accuracy** | 25.00% | 15.00% | 25.00% |
| **Mean Judge Score** | 2.00/5.00 | 1.60/5.00 | 2.00/5.00 |

## 2. Data Quality & Observability Status

| Check | Baseline | Corrupted | Repaired |
| :--- | :---: | :---: | :---: |
| **Overall Quality** | ✅ PASSED | ❌ FAILED | ✅ PASSED |
| **Total Rows** | 20 | 22 | 23 |
| **Null ID/Title Count** | 0 | 0 | 0 |
| **Stale Row Count** | 0 | 2 | 0 |
| **Is Fresh** | ✅ YES | ❌ NO | ✅ YES |

## 3. Analysis & Key Takeaways

1. **Impact of Corruption on Retrieval:**
   - Simulated corruption introduces noise, truncates titles, or blanks summaries, which significantly reduces the **Retrieval Hit Rate**.
   
2. **Impact of Corruption on Generation:**
   - Without clean and relevant context, the RAG agent's answers drop in quality, as shown by lower **Mean Token F1** and **Judge Accuracy**.
   
3. **Effectiveness of the Repair Process:**
   - Fetching fresh data from the raw source and re-running the ETL cleaning pipeline restores the database index, successfully restoring the retrieval and generation scores back to or near baseline levels.

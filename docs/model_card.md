# Model card — repeat purchase propensity v1

## Intended use

Rank customers for analyst review and demonstrate temporal ML engineering. Predict whether an identified historical customer buys again within 30 days. Outputs are decision support, not automatic outreach. Customer IDs are never predictive features.

## Data and populations

UCI Online Retail, one UK retailer, 2010–2011, with wholesale customers. Only customers with positive purchases in the previous 180 days are eligible. Missing-ID purchases remain in financial metrics but cannot inform customer features or labels. Exact duplicates and invalid financial records follow the documented cleaning policy.

## Temporal protocol

| Stage | As-of snapshots | Use |
|---|---|---|
| Train | Apr 1, May 1, Jun 1, 2011 | Fit candidates; 7,227 customer-snapshot rows |
| Validation | Aug 1, 2011 | Select candidate by average precision; 2,771 customers |
| Refit | Train + validation | Fit selected architecture once |
| Holdout | Oct 1, 2011 | Final evaluation; 2,925 customers |
| Score | Dec 10, 2011 | Score 3,477 historical customers, without labels |

Features end strictly before each cutoff. Labels cover the next 30 days; the pipeline refuses incomplete label windows. Training/validation outcome windows close before the next stage. Customers can recur across snapshots, intentionally evaluating future behavior of existing customers rather than generalization to unseen identities. Repeated customer rows are not independent training observations; frequent eligible customers contribute multiple snapshots.

## Candidates and baselines

Standardized logistic regression (`C=0.3`) and histogram gradient boosting (`150` iterations, `15` leaves, `L2=10`) use the same 10 numeric features. Parameters are fixed before validation; there is no broad search. Logistic regression wins validation AP and is refit on development data. Scaling is fit only inside the training pipeline.

The ranking baseline is an exponential recency heuristic (`exp(-recency/45)`). Its probabilities are arbitrary and not calibrated, so its Brier score is descriptive rather than a fair calibrated-probability benchmark. A constant development-rate baseline also appears in the comparison. Tie-based capacity metrics for the constant baseline depend on deterministic row order; the meaningful random-selection reference is the test prevalence.

## Held-out results

- Average precision: **0.554**, versus **0.351** recency baseline.
- ROC AUC: **0.694**; Brier score: **0.187**.
- Repeat-purchase prevalence: **30.9%**.
- Top 20% precision: **58.1%**; repeat-buyer capture: **37.7%**; lift: **1.88×**.
- AP 95% percentile bootstrap interval: **0.517–0.587**, 500 customer resamples with seed 42.

Average precision summarizes the precision-recall ranking; it is not trapezoidal PR-AUC and not classification accuracy. Capacity uses `ceil(0.20 × population)`. The bootstrap estimates uncertainty within this single test snapshot, not performance under a different season or retailer.

## Explainability and monitoring

Holdout permutation importance measures the AP drop when one feature is shuffled. It is a sensitivity diagnostic, not a causal explanation. Correlated features can share or mask importance. Calibration bins compare predicted probabilities with observed rates and show bin sizes.

Feature PSI compares train+validation with the final scoring snapshot using development quantiles and smoothed proportions. A value ≥0.2 is a heuristic review signal. Seasonality, changed eligibility, or customer mix may drive shifts. No later labels exist to confirm accuracy decay on the final snapshot.

## Limitations and required next work

This is a single-retailer historical case study. It does not establish incremental marketing impact, individualized treatment effects, profitability, or production readiness. Existing customers who bought before the dataset starts appear as newly observed. Missing customer IDs can bias populations. Country and demographic attributes are not used, but representation and business-context limitations remain. Inspect segment-level calibration and recent outcomes before real use.

A production campaign should randomize eligible customers to outreach and control, pre-register the primary incremental contribution metric, account for incentive/contact costs, and monitor unsubscribe/complaint rates. Do not infer savings by multiplying model accuracy by revenue.

## Reproduction

`python -m retailsignal.cli build` recreates the source fingerprint, data exports, model, and evidence. `reports/model_evaluation.json` is the authoritative numeric result. Dependency versions are recorded in `requirements-lock.txt`. The model artifact is intentionally not distributed; rebuild it locally and only load trusted joblib files.

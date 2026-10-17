# Interview walkthrough and study guide

## A 90-second project explanation

“I built RetailSignal to connect reliable reporting with customer decision support. I started with 541,909 public retail transaction lines, created an auditable cleaning pipeline, and used SQL to build revenue and cohort marts. A key decision was keeping anonymous sales in financial totals while excluding them from customer-level modeling.

“The dashboard lets an analyst investigate revenue, credits, retention, and a capacity-limited customer shortlist. I compared logistic regression with gradient boosting using time-based validation. On a later holdout, the selected model achieved 0.554 average precision versus 0.351 for a recency baseline. Its top 20% captured 37.7% of repeat purchasers.

“I also included Power BI project files, data-quality evidence, automated tests, and drift diagnostics. The model predicts repeat purchases, not incremental campaign lift, so the planning tool labels economic assumptions explicitly and proposes a controlled experiment before claiming business impact.”

Use this after you have run the project and can explain the design. The Power BI Desktop refresh remains a separate validation step; do not describe it as tested until you do that step.

## Five-minute demo

1. **Revenue overview:** explain gross, credits, net, and identity coverage. Filter France and export the same selected metrics. Point out the partial December period.
2. **Data trust:** explain 7,780 quarantined rows, duplicate assumptions, and source lineage.
3. **Customer retention:** explain month-zero retention, complete-month censoring, and why blanks differ from zeroes.
4. **Model evidence:** explain chronological cutoffs, validation selection, baseline, AP, lift, and calibration.
5. **Decision lab:** change capacity and cost. Explain why scenario contribution is not a forecast of realized profit.

## Questions to be ready for

**Why not drop every missing row?** Missing customer identity prevents individual attribution, but valid anonymous purchases still contribute revenue. Dropping them would understate gross sales by about 16.5%.

**What does 0.554 AP mean?** Average precision summarizes precision at positive-label positions across a ranking. It is neither 55.4% accuracy nor a business return. Compare it with prevalence and a practical ranking baseline.

**How did you prevent leakage?** Features use transactions strictly before the cutoff; labels use the next 30 days. The pipeline rejects censored label windows, and a test changes future data to confirm historical features are unchanged.

**Why are some customers in both training and test?** This evaluates later behavior of existing customers. IDs are not features. A separate new-customer experiment would need customer-disjoint evaluation and a different eligibility definition.

**Why did you choose logistic regression?** It won the predefined validation AP comparison. Simplicity alone was not the selection criterion, and the holdout was not used to choose the winner.

**Why is retention month zero 100%?** Every cohort member has a first observed purchase in that month by definition. Later months count customers with at least one positive purchase divided by the original cohort size.

**What is not additive?** Distinct customers across days. Grain mismatches also inflate revenue if customer/cohort tables are joined directly to invoice lines. The BI model keeps these separate.

**What would you change for production?** Recent data, accounting sign-off, versioned artifact releases, an orchestrated refresh, authorization, monitoring with delayed labels, and an A/B experiment to estimate incremental value.

## Role-specific evidence

| Role | Show and explain |
|---|---|
| Data analyst | SQL KPI definitions, EDA notebook, filtering, cohorts, findings |
| Business analyst | Requirements, stakeholder decisions, acceptance criteria, experiment design |
| Data scientist | Temporal evaluation, baseline choice, AP, calibration, uncertainty |
| Data engineer | Typed ingest, fingerprints, quarantine, idempotent SQL, data contracts, CI |
| AI data engineer | Feature snapshots, model artifact contract, batch scoring, distribution monitoring |
| AI data analyst | Predictive signals interpreted alongside business KPIs and uncertainty |

The project demonstrates conventional machine learning. It does not claim LLM/RAG implementation, distributed big-data operations, or cloud deployment.

## Resume bullets to use after reviewing the work

- Built a reproducible Python/SQL retail analytics pipeline processing 541K transaction lines, with auditable quarantine, financial reconciliation, and customer-retention marts.
- Developed an interactive dashboard and editable Power BI project with revenue, cohort, and customer-prioritization views backed by documented KPI definitions.
- Evaluated repeat-purchase models using time-based validation; achieved 0.554 holdout average precision and 1.88× top-quintile lift, with calibration and drift diagnostics.

Do not turn these into claims of employer impact, realized revenue improvement, or Power BI runtime validation until you have evidence for those claims.

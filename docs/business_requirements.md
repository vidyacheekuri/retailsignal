# Business requirements and acceptance criteria

## Stakeholders and decisions

| Stakeholder | Decision | Output |
|---|---|---|
| Commercial lead | Which markets need investigation? | Net revenue, credit burden, concentration |
| Operations analyst | Can these numbers be trusted? | Row reconciliation, quarantine, source fingerprint |
| Customer analyst | Which cohorts and segments return? | Complete-month retention and segment rules |
| Campaign planner | Which customers fit limited review capacity? | Scored shortlist and scenario assumptions |
| Model reviewer | Does ML beat a simple rule? | Temporal holdout, baseline, calibration, uncertainty |

## Acceptance criteria

1. Every source row is accepted or quarantined exactly once; duplicates have an explicit policy.
2. Gross minus credits equals net in pennies, and warehouse totals match accepted records.
3. Anonymous revenue is retained and customer-identity coverage is disclosed.
4. Dashboard date/country filters update only the stated reporting scope; exports match that selection.
5. Cohorts use fixed denominators, show observed zeroes, and leave unobserved future periods blank.
6. Features cannot change when future transaction values change. Incomplete labels are rejected.
7. Model selection uses validation, not the holdout; a simple baseline is published.
8. Capacity-limited shortlist and scenario economics respond to user inputs.
9. Scenario values are labeled assumptions; no realized ROI is claimed.
10. One documented command rebuilds results; automated checks run in CI.

## Suggested campaign experiment

Business hypothesis: a carefully targeted offer can increase incremental contribution after all costs. Propensity scores are useful for stratification, not proof of uplift. Randomize within score/segment strata, keep a control group, define one primary outcome and observation window, and calculate sample size from a business-approved minimum detectable effect. The dataset contains no actual campaigns, costs, consent, or margin data, so experiment results cannot be fabricated here.

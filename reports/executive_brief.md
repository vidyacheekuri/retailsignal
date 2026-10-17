# RetailSignal · executive brief

Historical case study: December 2010–December 2011. Currency: GBP. No company deployment or realized ROI is claimed.

Processed **541,909** source lines into **534,129** accepted ledger lines; **7,780** rows are quarantined.

Recorded gross revenue: **£10,642,110.80**. Credits: **£893,979.73**. Net revenue: **£9,748,131.07**.

## Which markets contribute the most net revenue?
United Kingdom contributes 84.0% of recorded net revenue. Evaluate concentration risk before assuming this mix transfers to another retailer.

## Where is the credit burden highest?
Markets are compared only above £10,000 gross revenue. Credits are ledger events, not matched product returns; investigate timing and adjustments before attributing causes.

## How much revenue lacks a customer identity?
£1,754,902 (16.5%) of gross revenue has no customer ID. It remains in revenue reporting but is excluded from customer-level modeling and cohorts.

## Which complete month grew the most?
2011-05 has the largest month-over-month net revenue increase (46.7%) among complete months. This is descriptive growth, not a causal result.

## Customer prioritization
The selected logistic regression model achieved test average precision **0.554**, versus **0.351** for a recency heuristic. At 20% capacity, precision is **58.1%**, capturing **37.7%** of repeat purchasers (**1.88×** random-selection lift).

This predicts natural repeat purchase, not incremental response to outreach. High propensity alone does not establish who will benefit from a promotion.

## Recommended next decisions
1. Audit the largest credit events and price adjustments; the dataset cannot attribute their causes.
2. Improve customer identification at checkout and measure coverage before expanding personalization.
3. Run a randomized campaign with an untreated control. Measure incremental contribution margin after incentive and contact costs.
4. Refit and revalidate on recent operational data before deployment; this historical retailer has wholesale activity and limited season coverage.

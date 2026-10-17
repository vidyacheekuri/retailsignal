"""Auditable business answers, computed from governed metrics; no LLM required."""
from pathlib import Path
import pandas as pd


def answer(question: str, root: Path) -> tuple[str, pd.DataFrame]:
    daily = pd.read_csv(root / "data/exports/mart_daily_country.csv")
    monthly = pd.read_csv(root / "data/exports/mart_monthly.csv")
    if question == "Which markets contribute the most net revenue?":
        table = daily.groupby("country")[["gross_revenue", "credits", "net_revenue"]].sum().sort_values("net_revenue", ascending=False)
        top = table.iloc[0]
        share = top.net_revenue / table.net_revenue.sum()
        return f"{table.index[0]} contributes {share:.1%} of recorded net revenue. Evaluate concentration risk before assuming this mix transfers to another retailer.", table.head(10).reset_index()
    if question == "Where is the credit burden highest?":
        table = daily.groupby("country")[["gross_revenue", "credits"]].sum()
        table = table[table.gross_revenue >= 10000].copy()
        table["credit_ratio"] = table.credits / table.gross_revenue
        table = table.sort_values("credit_ratio", ascending=False)
        return "Markets are compared only above £10,000 gross revenue. Credits are ledger events, not matched product returns; investigate timing and adjustments before attributing causes.", table.reset_index()
    if question == "How much revenue lacks a customer identity?":
        value = daily.anonymous_gross.sum()
        share = value / daily.gross_revenue.sum()
        return f"£{value:,.0f} ({share:.1%}) of gross revenue has no customer ID. It remains in revenue reporting but is excluded from customer-level modeling and cohorts.", pd.DataFrame({"measure": ["Anonymous gross revenue", "Identified gross revenue"], "gbp": [value, daily.gross_revenue.sum() - value]})
    if question == "Which complete month grew the most?":
        table = monthly[~monthly.partial_month].copy()
        table["net_growth"] = table.net_revenue.pct_change()
        valid = table.dropna(subset=["net_growth"])
        best = valid.loc[valid.net_growth.idxmax()]
        return f"{best.month} has the largest month-over-month net revenue increase ({best.net_growth:.1%}) among complete months. This is descriptive growth, not a causal result.", table[["month", "net_revenue", "net_growth"]]
    raise ValueError("Choose one of the supported, auditable questions")


QUESTIONS = ["Which markets contribute the most net revenue?", "Where is the credit burden highest?",
             "How much revenue lacks a customer identity?", "Which complete month grew the most?"]


def write_brief(root: Path, quality: dict, model: dict) -> None:
    sections = ["# RetailSignal · executive brief", "", "Historical case study: December 2010–December 2011. Currency: GBP. No company deployment or realized ROI is claimed.", "",
        f"Processed **{quality['source_rows']:,}** source lines into **{quality['accepted_rows']:,}** accepted ledger lines; **{quality['rejected_rows']:,}** rows are quarantined.", "",
        f"Recorded gross revenue: **£{quality['gross_gbp']:,.2f}**. Credits: **£{quality['credits_gbp']:,.2f}**. Net revenue: **£{quality['net_gbp']:,.2f}**.", ""]
    for question in QUESTIONS:
        text, _ = answer(question, root)
        sections += [f"## {question}", text, ""]
    m = model["test"]
    sections += ["## Customer prioritization", f"The selected {model['selected_model'].lower()} model achieved test average precision **{m['average_precision']:.3f}**, versus **{model['recency_baseline_ap']:.3f}** for a recency heuristic. At 20% capacity, precision is **{m['precision_at_20pct']:.1%}**, capturing **{m['capture_at_20pct']:.1%}** of repeat purchasers (**{m['lift_at_20pct']:.2f}×** random-selection lift).",
        "", "This predicts natural repeat purchase, not incremental response to outreach. High propensity alone does not establish who will benefit from a promotion.", "",
        "## Recommended next decisions", "1. Audit the largest credit events and price adjustments; the dataset cannot attribute their causes.",
        "2. Improve customer identification at checkout and measure coverage before expanding personalization.",
        "3. Run a randomized campaign with an untreated control. Measure incremental contribution margin after incentive and contact costs.",
        "4. Refit and revalidate on recent operational data before deployment; this historical retailer has wholesale activity and limited season coverage.", ""]
    (root / "reports/executive_brief.md").write_text("\n".join(sections))

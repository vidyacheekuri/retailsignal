"""Portfolio dashboard. Uses checked-in aggregates; raw data is not required to explore."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from retailsignal.insights import QUESTIONS, answer

st.set_page_config(page_title="RetailSignal | Decision Intelligence", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container {padding-top:2rem; padding-bottom:2rem; max-width:1500px}
[data-testid="stSidebar"] {background:#101f2e}
[data-testid="stSidebar"] * {color:#f0f5f7}
[data-testid="stSidebar"] [data-testid="stLinkButton"] a {background:#244353;border-color:#406171}
[data-testid="stMetric"] {background:#fff;border:1px solid #dfe7e9;border-radius:12px;padding:18px 20px}
[data-testid="stMetricLabel"] {color:#627781;text-transform:uppercase;font-size:12px;letter-spacing:1px}
h1,h2,h3 {letter-spacing:-.7px}
.hero {background:#102a38;border-radius:16px;padding:32px 36px;color:#fff;margin-bottom:24px}
.eyebrow {font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#6ee7c0;font-weight:700}
.hero h1 {font-size:38px;margin:8px 0;color:#fff}
.hero p {color:#c2d1d7;max-width:800px;margin:0;font-size:15px}
.note {border-left:3px solid #13a880;padding:10px 16px;background:#edf7f3;color:#254b42;margin:18px 0}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load(name):
    return pd.read_csv(ROOT / "data/exports" / f"{name}.csv")


def chart(fig, height=340):
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=35, b=10),
                      font=dict(family="Arial", color="#395363"), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", colorway=["#0d9f83", "#2e5b8c", "#e49b49", "#b96b6b"],
                      legend=dict(orientation="h", y=1.12, x=0), hovermode="closest")
    st.plotly_chart(fig, use_container_width=True, theme=None)


if not (ROOT / "reports/model_evaluation.json").exists():
    st.error("Build the project first: python -m retailsignal.cli build")
    st.stop()
quality = json.loads((ROOT / "reports/data_quality.json").read_text())
model = json.loads((ROOT / "reports/model_evaluation.json").read_text())

with st.sidebar:
    st.markdown("## ◈ RetailSignal")
    st.caption("REVENUE · CUSTOMERS · DECISIONS")
    page = st.radio("Workspace", ["Revenue overview", "Customer retention", "Decision lab", "Model evidence", "Data trust", "Analyst desk"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Historical case study**")
    st.caption("UCI Online Retail\n\nDec 2010 — Dec 2011\n\nCurrency: GBP (£)")
    st.caption("Built by Sree Vidya Cheekuri")
    st.link_button("Project on GitHub", "https://github.com/vidyacheekuri/retailsignal")

subtitles = {
 "Revenue overview": ("Know where value flows.", "A reconciled view of sales, credits, and market concentration. Every figure traces back to the transaction ledger."),
 "Customer retention": ("See who comes back.", "Cohort retention and behavior segments reveal how customer relationships develop over time."),
 "Decision lab": ("Turn signals into a shortlist.", "Explore customer propensity and campaign economics with explicit assumptions and a fixed outreach capacity."),
 "Model evidence": ("Make the model earn trust.", "Temporal validation, a simple baseline, calibration, and transparent limitations—not just an accuracy score."),
 "Data trust": ("Trust starts with the ledger.", "Follow every source row through validation, quarantine, and financial reconciliation."),
 "Analyst desk": ("From a question to evidence.", "Curated business questions return reproducible answers and the supporting data. No API key required.")}
heading, subtitle = subtitles[page]
st.markdown(f'<div class="hero"><div class="eyebrow">RetailSignal / {page}</div><h1>{heading}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

if page == "Revenue overview":
    daily = load("mart_daily_country")
    daily["date_key"] = pd.to_datetime(daily.date_key)
    a, b = st.columns([2, 1])
    countries = a.multiselect("Markets", sorted(daily.country.unique()), placeholder="All markets")
    dates = b.date_input("Reporting period", (daily.date_key.min().date(), daily.date_key.max().date()),
                        min_value=daily.date_key.min().date(), max_value=daily.date_key.max().date())
    if len(dates) != 2:
        st.info("Select both a start and an end date.")
        st.stop()
    d = daily[daily.date_key.between(pd.Timestamp(dates[0]), pd.Timestamp(dates[1]))]
    if countries:
        d = d[d.country.isin(countries)]
    if d.empty:
        st.info("No transactions match this selection.")
        st.stop()
    gross, credits, net, orders = [d[c].sum() for c in ["gross_revenue", "credits", "net_revenue", "orders"]]
    for col, label, value in zip(st.columns(4), ["Net revenue", "Gross revenue", "Credit / gross", "Sales orders"],
                               [f"£{net/1e6:.2f}M" if abs(net)>=1e6 else f"£{net:,.0f}", f"£{gross/1e6:.2f}M" if gross>=1e6 else f"£{gross:,.0f}", f"{credits/gross:.1%}" if gross else "—", f"{orders:,.0f}"]):
        col.metric(label, value)
    left, right = st.columns([1.7, 1])
    with left:
        st.subheader("The revenue story")
        monthly = d.assign(month=d.date_key.dt.to_period("M").astype(str)).groupby("month", as_index=False)[["gross_revenue", "net_revenue"]].sum()
        monthly = monthly.rename(columns={"gross_revenue":"Gross revenue", "net_revenue":"Net revenue"})
        fig = px.line(monthly, x="month", y=["Gross revenue", "Net revenue"], markers=True,
                      labels={"value": "Revenue (£)", "month": "", "variable": "Metric"})
        chart(fig)
        st.caption("December 2011 ends on December 9. Date filters may also create partial months; compare like-for-like periods.")
    with right:
        st.subheader("Markets that matter")
        markets = d.groupby("country", as_index=False).net_revenue.sum().nlargest(7, "net_revenue").sort_values("net_revenue")
        chart(px.bar(markets, x="net_revenue", y="country", orientation="h", labels={"net_revenue":"Net revenue (£)","country":""}))
    a, b = st.columns([1, 1])
    with a:
        st.subheader("Revenue bridge")
        chart(go.Figure(go.Waterfall(x=["Gross sales", "Credits", "Net revenue"], measure=["absolute", "relative", "total"],
            y=[gross, -credits, net], increasing={"marker":{"color":"#0d9f83"}}, decreasing={"marker":{"color":"#d68b59"}}, totals={"marker":{"color":"#2e5b8c"}})), 280)
    with b:
        st.subheader("A clearer reading")
        st.markdown(f"**£{credits:,.0f} in credits** separates gross sales from net revenue. Credits include cancellations and adjustments; they are not linked to original orders.")
        coverage = 1 - d.anonymous_gross.sum()/gross if gross else 0
        st.markdown(f"**{coverage:.1%} of gross revenue has a customer ID.** Anonymous purchases remain in financial totals but cannot be assigned to customer cohorts.")
        st.caption("Gross order value = positive sales / distinct sales invoices. Net revenue is a ledger proxy, not audited profit. Revenue filters apply only to this page.")
        st.download_button("Download selected daily metrics", d.to_csv(index=False), "retailsignal_metrics.csv", "text/csv")

elif page == "Customer retention":
    st.caption("Scope: all markets. Cohorts use identified customers and positive purchases. Only complete calendar months are shown.")
    cohorts = load("mart_cohorts")
    matrix = cohorts.pivot(index="cohort", columns="month_index", values="retention")
    st.subheader("Repeat purchase by acquisition cohort")
    fig = px.imshow(matrix, text_auto=".0%", color_continuous_scale=["#f0f6f5", "#99d5c5", "#087f70"], zmin=0, zmax=1,
                    labels={"x":"Months since first observed purchase", "y":"First observed purchase month", "color":"Retention"}, aspect="auto")
    chart(fig, 450)
    st.caption("Blank cells are unobserved future periods. Zero is an observed month with no repeat buyers. December 2010 includes existing customers first observed in this dataset.")
    a, b = st.columns(2)
    segments = load("mart_segments")
    with a:
        st.subheader("Customer behavior segments")
        chart(px.bar(segments, x="customers", y="segment", orientation="h", labels={"segment":"", "customers":"Customers"}))
    with b:
        st.subheader("Rules you can explain")
        st.markdown("- **Champions:** purchased in 30 days, at least 4 orders.\n- **Recent shoppers:** purchased in 30 days, fewer than 4 orders.\n- **Lapsing loyal:** last purchase over 60 days ago, at least 3 orders.\n- **Dormant:** last purchase over 90 days ago, after the prior rules.\n- **Developing:** remaining active-history customers.")
        st.caption("Segments use the 180-day lookback at December 10, 2011. Rules are evaluated in this order. They are interpretable business rules, not learned clusters.")

elif page == "Decision lab":
    scores = load("customer_scores")
    st.caption("Frozen historical scores as of December 10, 2011 · all markets · 30-day repeat-purchase propensity")
    a, b = st.columns([1, 2])
    with a:
        segment = st.selectbox("Audience", ["All segments", *sorted(scores.segment.unique())])
        audience = scores if segment == "All segments" else scores[scores.segment == segment]
        capacity = st.slider("Outreach capacity", 1, max(2, len(audience)), min(200, len(audience)))
        uplift = st.slider("Assumed incremental conversion (percentage points)", 0.0, 15.0, 2.0, .5) / 100
        contribution = st.number_input("Contribution per incremental order (£)", min_value=0.0, value=25.0)
        contact_cost = st.number_input("All-in cost per contact (£)", min_value=0.0, value=.50, step=.10)
    selected = audience.nlargest(capacity, "repeat_probability").copy()
    with b:
        st.subheader("Capacity-aware planning")
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected customers", f"{len(selected):,}")
        c2.metric("Mean repeat propensity", f"{selected.repeat_probability.mean():.1%}")
        scenario = len(selected) * (uplift * contribution - contact_cost)
        c3.metric("Scenario contribution", f"£{scenario:,.0f}")
        st.warning("Scenario only: incremental conversion and contribution are assumptions. The model estimates natural repeat purchase, not campaign lift. A randomized experiment is needed to measure impact.")
        chart(px.histogram(audience, x="repeat_probability", nbins=25, labels={"repeat_probability":"Predicted repeat probability"}), 240)
    st.subheader("Your review queue")
    st.dataframe(selected[["customer_id", "segment", "repeat_probability", "recency_days", "orders_180d", "gross_180d"]], hide_index=True,
        column_config={"repeat_probability":st.column_config.ProgressColumn("Repeat propensity", min_value=0, max_value=1, format="%.2f")})
    st.download_button("Export customer shortlist", selected.to_csv(index=False), "customer_shortlist.csv", "text/csv")
    st.caption("Public dataset IDs are pseudonymous. Export is a planning demonstration, not a live campaign list. Probabilities are estimates; inspect calibration before using them in forecasts.")

elif page == "Model evidence":
    m = model["test"]
    for col, label, value in zip(st.columns(4), ["Test average precision", "Top 20% lift", "Top 20% precision", "Test customers"],
                               [f"{m['average_precision']:.3f}", f"{m['lift_at_20pct']:.2f}×", f"{m['precision_at_20pct']:.1%}", f"{m['customers']:,}"]):
        col.metric(label, value)
    st.markdown(f"**Selected model: {model['selected_model']}** · Test AP 95% bootstrap interval: {model['test_ap_ci95'][0]:.3f}–{model['test_ap_ci95'][1]:.3f}.")
    st.info("Train: Apr / May / Jun 2011 snapshots → validate: Aug 1 → refit on development data → test: Oct 1. Every label covers the following 30 days. Customers may recur across time; this evaluates future behavior of existing customers.")
    left, right = st.columns(2)
    with left:
        st.subheader("Does the ranking beat simple rules?")
        metrics = load("model_metrics")
        chart(px.bar(metrics[metrics.split == "test"], x="model", y="average_precision", labels={"average_precision":"Average precision", "model":""}))
    with right:
        st.subheader("Do probabilities match outcomes?")
        calibration = load("model_calibration")
        fig = px.scatter(calibration, x="predicted", y="observed", size="customers", labels={"predicted":"Mean predicted probability", "observed":"Observed repeat rate"})
        fig.add_shape(type="line", x0=0, x1=1, y0=0, y1=1, line=dict(dash="dash",color="#9eafb7"))
        fig.update_xaxes(range=[0,1]); fig.update_yaxes(range=[0,1])
        chart(fig)
    st.subheader("What does the model rely on?")
    importance = load("model_importance").sort_values("importance")
    chart(px.bar(importance, x="importance", y="feature", error_x="std", orientation="h", labels={"importance":"Holdout AP decrease after permutation", "feature":""}), 340)
    st.caption("Permutation importance measures sensitivity, not causality. Correlated features can share importance. Test data is used for final reporting only, not model selection.")
    with st.expander("Full comparison and limitations"):
        st.dataframe(metrics, hide_index=True)
        st.markdown("One retailer, 2010–2011, wholesale activity, and limited season coverage restrict generalization. Missing IDs exclude some purchases from modeling. Bootstrap uncertainty covers customers in one test snapshot, not future economic regimes. No causal uplift, automated outreach, or realized savings are claimed.")
    st.subheader("Monitor the scoring population")
    st.dataframe(load("feature_drift"), hide_index=True)
    st.caption("Population Stability Index compares development snapshots with December scoring data using development quantile bins. PSI ≥ 0.2 is a review heuristic, not proof of failure. Seasonal change and customer mix may explain shifts; future outcomes are unavailable here.")

elif page == "Data trust":
    for col, key, label in zip(st.columns(4), ["source_rows", "accepted_rows", "rejected_rows", "exact_duplicates"], ["Source rows", "Accepted rows", "Quarantined rows", "Exact duplicates"]):
        col.metric(label, f"{quality[key]:,}")
    reconciliation = quality["source_rows"] == quality["accepted_rows"] + quality["rejected_rows"]
    st.success("PASS · Source rows = accepted + quarantined" if reconciliation else "Reconciliation failed")
    st.subheader("A documented cleaning policy")
    st.dataframe(pd.DataFrame([
        ["Exact duplicate source lines", "Keep first; quarantine copies", quality["exact_duplicates"]],
        ["Invalid transaction", "Quarantine; retain reason and source row", quality["invalid_transactions_excluding_duplicates"]],
        ["Missing customer ID", "Keep revenue; exclude customer modeling", quality["accepted_missing_customer"]],
        ["Sub-penny unit prices", "Round unit price to pennies; disclose net effect", quality["subpenny_price_rows"]],
    ], columns=["Check", "Policy", "Affected rows"]), hide_index=True)
    st.markdown(f"Unit-price rounding changes recorded net revenue by **£{quality['rounding_net_difference_gbp']:,.4f}** compared with unrounded source arithmetic.")
    st.caption("Exact duplicate removal is an explicit assumption: identical invoice lines could be intentional. Quarantine enables audit and alternative policies. Invalid = missing key/date/country, non-finite amounts, non-positive price, zero/non-integer quantity, or a positive-quantity cancellation.")
    st.subheader("Source lineage")
    st.code(quality["sha256"], language=None)
    st.markdown("[UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) · Daqing Chen (2015) · CC BY 4.0 · DOI: 10.24432/C5BW33")
    st.json(quality, expanded=False)

elif page == "Analyst desk":
    question = st.selectbox("Business question", QUESTIONS)
    response, evidence = answer(question, ROOT)
    st.subheader("Finding")
    st.write(response)
    st.subheader("Supporting evidence")
    st.dataframe(evidence, hide_index=True)
    st.caption("Deterministic analysis over curated SQL marts. This interface is intentionally limited to supported questions; it is not a generative AI assistant.")
    st.download_button("Download executive brief", (ROOT / "reports/executive_brief.md").read_text(), "retailsignal_brief.md", "text/markdown")

st.divider()
st.caption("RETAILSIGNAL  /  Reproducible analysis. Explicit assumptions. Decisions backed by evidence.")

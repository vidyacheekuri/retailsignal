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

st.set_page_config(page_title="RetailSignal | Customer & revenue analytics", page_icon="▥", layout="wide")
st.markdown(f"<style>{(ROOT / 'assets/dashboard.css').read_text()}</style>", unsafe_allow_html=True)
px.defaults.color_discrete_sequence = ["#E1572A", "#262E33", "#8B9DAB", "#C5AE76"]


@st.cache_data
def load(name):
    return pd.read_csv(ROOT / "data/exports" / f"{name}.csv")


def chart(fig, height=340):
    fig.update_layout(template="plotly_white", height=height,
                      margin=dict(l=0, r=12, t=30, b=5),
                      font=dict(family="IBM Plex Sans, Arial, sans-serif", size=12, color="#55616A"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      colorway=px.defaults.color_discrete_sequence,
                      legend=dict(orientation="h", y=1.15, x=0, title_text=""),
                      hoverlabel=dict(bgcolor="#262E33", font_color="#FFFFFF"), hovermode="closest")
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#DDE0E1", automargin=True)
    fig.update_yaxes(gridcolor="#E9EBEB", zeroline=False, automargin=True)
    st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={"displayModeBar": False, "responsive": True})


def data_table(frame):
    labels = {"country": "Market", "gross_revenue": "Gross sales (£)", "net_revenue": "Net revenue (£)",
              "credits": "Credits (£)", "credit_ratio": "Credits / gross", "gbp": "Revenue (£)",
              "net_growth": "Monthly growth", "roc_auc": "ROC AUC", "psi": "PSI",
              "precision_at_20pct": "Precision · top 20%", "lift_at_20pct": "Lift · top 20%",
              "capture_at_20pct": "Capture · top 20%", "reference_mean": "Development mean",
              "current_mean": "Scoring mean"}
    formats = {}
    for col in frame.select_dtypes(include="number"):
        if col in {"positive_rate", "credit_ratio", "net_growth", "precision_at_20pct", "capture_at_20pct"}:
            formats[col] = "{:.1%}"
        elif col in {"customers", "gross_revenue", "net_revenue", "credits", "gbp"}:
            formats[col] = "{:,.0f}"
        else:
            formats[col] = "{:,.3f}"
    st.dataframe(frame.style.format(formats, na_rep="—"), hide_index=True,
                 column_config={col: labels.get(col, col.replace("_", " ").capitalize()) for col in frame.columns})


def section(label, title):
    st.markdown(f'<div class="section-label">{label}</div><h3>{title}</h3>', unsafe_allow_html=True)


def navigate(destination):
    st.session_state.workspace = destination


if not (ROOT / "reports/model_evaluation.json").exists():
    st.error("Build the project first: python -m retailsignal.cli build")
    st.stop()
quality = json.loads((ROOT / "reports/data_quality.json").read_text())
model = json.loads((ROOT / "reports/model_evaluation.json").read_text())

st.markdown("""<div class="masthead">
  <div class="brand"><span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>retail<span class="brand-light">signal</span><span class="brand-dot">.</span></div>
  <div class="masthead-meta"><span class="archive-dot"></span> CUSTOMER & REVENUE ANALYTICS<br><span class="edition">UCI ONLINE RETAIL / HISTORICAL STUDY</span></div>
</div>""", unsafe_allow_html=True)
page_labels = {"Revenue overview": "Revenue", "Customer retention": "Customers", "Decision lab": "Campaign planner",
               "Model evidence": "Model performance", "Data trust": "Data quality", "Analyst desk": "Business questions"}
with st.container(key="navigation"):
    page = st.radio("Workspace", list(page_labels), horizontal=True, label_visibility="collapsed",
                    format_func=page_labels.get, key="workspace")
subtitles = {
 "Revenue overview": ("01 / TRADING REPORT", "Revenue overview", "Sales, credits, and the markets behind them. Choose a period to take a closer look."),
 "Customer retention": ("02 / CUSTOMER BEHAVIOUR", "Who comes back?", "Follow repeat purchases over time, then examine the customers behind them."),
 "Decision lab": ("03 / CAMPAIGN PLANNING", "Build a customer shortlist", "Set your audience and budget assumptions. See what a campaign would need to earn its keep."),
 "Model evidence": ("04 / MODEL PERFORMANCE", "How good is the ranking?", "Compare the model with a simple rule, and check where its estimates hold up."),
 "Data trust": ("05 / DATA QUALITY", "Account for every row", "What was kept, what was set aside, and how those choices affect the numbers."),
 "Analyst desk": ("06 / BUSINESS QUESTIONS", "Start with a question", "Four useful questions about this retailer, with the working behind each answer.")}
kicker, heading, subtitle = subtitles[page]
st.markdown(f'<div class="page-heading"><div><div class="section-label">{kicker}</div><h1>{heading}</h1><p>{subtitle}</p></div><div class="period-stamp">DEC 2010 — DEC 2011<br><strong>GBP / £</strong></div></div>', unsafe_allow_html=True)

if page == "Revenue overview":
    daily = load("mart_daily_country")
    daily["date_key"] = pd.to_datetime(daily.date_key)
    with st.container(key="filters"):
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
    with st.container(key="summary"):
        for col, label, value, help_text in zip(st.columns(4),
                ["Net revenue", "Gross sales", "Credits / gross", "Sales orders"],
                [f"£{net/1e6:.2f}m" if abs(net)>=1e6 else f"£{net:,.0f}",
                 f"£{gross/1e6:.2f}m" if gross>=1e6 else f"£{gross:,.0f}",
                 f"{credits/gross:.1%}" if gross else "—", f"{orders:,.0f}"],
                ["Gross sales less credits", "Positive sales before credits", "Credits as a share of gross sales", "Distinct positive-sales invoices"]):
            col.metric(label, value, help=help_text)
    market_totals = d.groupby("country", as_index=False).net_revenue.sum().sort_values("net_revenue", ascending=False)
    leader = market_totals.iloc[0]
    coverage = 1 - d.anonymous_gross.sum()/gross if gross else 0
    left, right = st.columns([1.8, 1], gap="medium")
    with left, st.container(border=True, key="sales_panel"):
        section("MONTH BY MONTH", "Sales & credits")
        monthly = d.assign(month=d.date_key.dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False)[["net_revenue", "credits"]].sum()
        fig = go.Figure()
        fig.add_bar(x=monthly.month, y=monthly.net_revenue, name="Net revenue", marker_color="#E1572A",
                    hovertemplate="%{x|%b %Y}<br>Net revenue: £%{y:,.0f}<extra></extra>")
        fig.add_bar(x=monthly.month, y=monthly.credits, name="Credits", marker_color="#CED5D8",
                    hovertemplate="%{x|%b %Y}<br>Credits: £%{y:,.0f}<extra></extra>")
        fig.update_layout(barmode="relative", bargap=.32)
        fig.update_yaxes(tickprefix="£", tickformat="~s", title=None)
        fig.update_xaxes(tickmode="array", tickvals=monthly.month,
                         ticktext=[date.strftime("%b '%y") if i in (0, len(monthly)-1) else date.strftime("%b")
                                   for i, date in enumerate(monthly.month)], tickangle=-35, title=None)
        chart(fig, 310)
        st.caption("Stack height equals gross sales when net revenue is positive. December 2011 ends on the 9th; date filters can also create partial months.")
    with right, st.container(border=True, key="markets_panel"):
        section("MARKET MIX", "Where sales happen")
        markets = market_totals.head(6).sort_values("net_revenue")
        fig = px.bar(markets, x="net_revenue", y="country", orientation="h",
                     labels={"net_revenue":"", "country":""})
        fig.update_traces(marker_color=["#CED5D8"]*(len(markets)-1)+["#262E33"],
                          texttemplate="£%{x:.3s}", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>Net revenue: £%{x:,.0f}<extra></extra>")
        fig.update_layout(margin=dict(r=55), bargap=.48)
        fig.update_xaxes(visible=False, range=[min(0, markets.net_revenue.min()*1.3), max(1, markets.net_revenue.max()*1.3)])
        fig.update_yaxes(showgrid=False)
        chart(fig, 310)
        if net > 0:
            st.caption(f"{leader.country} accounts for {leader.net_revenue/net:.1%} of net revenue in this selection. Showing the top {len(markets)} markets.")
        else:
            st.caption("Markets ranked by net revenue. Credits can exceed sales in a selected period.")
    with st.container(key="reading"):
        st.markdown(f'<div class="reading"><span class="reading-label">A CLOSER LOOK</span><p><strong>{coverage:.1%} of gross sales can be linked to a customer.</strong> The rest stays in the revenue totals, but is excluded from retention and customer scoring.</p></div>', unsafe_allow_html=True)
    a, b = st.columns([1.2, 1], gap="medium")
    with a, st.container(border=True, key="ledger_panel"):
        section("LEDGER CHECK", "From gross to net")
        fig = go.Figure(go.Waterfall(x=["Gross sales", "Credits", "Net revenue"], measure=["absolute", "relative", "total"],
            y=[gross, -credits, net], text=[f"£{gross:,.0f}", f"−£{credits:,.0f}", f"£{net:,.0f}"], textposition="outside",
            connector={"line":{"color":"#CED5D8"}}, increasing={"marker":{"color":"#262E33"}},
            decreasing={"marker":{"color":"#C4CDD1"}}, totals={"marker":{"color":"#E1572A"}}))
        fig.update_yaxes(tickprefix="£", tickformat="~s")
        chart(fig, 280)
    with b, st.container(border=True, key="notes_panel"):
        section("READING THE NUMBERS", "What to keep in mind")
        st.markdown(f"**£{credits:,.0f} in credits** separates gross sales from net revenue. Credits include cancellations and adjustments; they cannot be matched to original orders here.")
        st.caption("Net revenue is a ledger measure, not profit. These filters affect the revenue page only; customer and model pages use their stated historical snapshots.")
        st.download_button("Download this selection ↓", d.to_csv(index=False), "retailsignal_metrics.csv", "text/csv", use_container_width=True)
        st.button("Explore customer retention →", on_click=navigate, args=("Customer retention",), use_container_width=True)

elif page == "Customer retention":
    st.caption("Scope: all markets. Cohorts use identified customers and positive purchases. Only complete calendar months are shown.")
    cohorts = load("mart_cohorts")
    matrix = cohorts.pivot(index="cohort", columns="month_index", values="retention")
    st.subheader("Repeat purchase by acquisition cohort")
    fig = px.imshow(matrix, text_auto=".0%", color_continuous_scale=["#FAF3E9", "#EBAD7E", "#BB431C"], zmin=0, zmax=1,
                    labels={"x":"Months since first observed purchase", "y":"First observed purchase month", "color":"Retention"}, aspect="auto")
    fig.update_yaxes(type="category", tickmode="array", tickvals=matrix.index,
                     ticktext=pd.to_datetime(matrix.index).strftime("%b %Y"))
    fig.update_coloraxes(colorbar_tickformat=".0%")
    chart(fig, 450)
    st.caption("Blank cells are unobserved future periods. Zero is an observed month with no repeat buyers. December 2010 includes existing customers first observed in this dataset.")
    a, b = st.columns(2)
    segments = load("mart_segments")
    with a:
        st.subheader("Customer behavior segments")
        chart(px.bar(segments, x="customers", y="segment", orientation="h", labels={"segment":"", "customers":"Customers"}))
    with b:
        st.subheader("How the segments are defined")
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
        st.subheader("The campaign arithmetic")
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected customers", f"{len(selected):,}")
        c2.metric("Mean repeat propensity", f"{selected.repeat_probability.mean():.1%}")
        scenario = len(selected) * (uplift * contribution - contact_cost)
        c3.metric("Scenario contribution", f"£{scenario:,.0f}")
        st.warning("Scenario only: incremental conversion and contribution are assumptions. The model estimates natural repeat purchase, not campaign lift. A randomized experiment is needed to measure impact.")
        chart(px.histogram(audience, x="repeat_probability", nbins=25, labels={"repeat_probability":"Predicted repeat probability"}), 240)
    st.subheader("Customer shortlist")
    st.dataframe(selected[["customer_id", "segment", "repeat_probability", "recency_days", "orders_180d", "gross_180d"]], hide_index=True,
        column_config={"customer_id": "Customer ID", "segment": "Segment", "recency_days": "Days since purchase",
                       "orders_180d": "Orders · 180 days", "gross_180d": st.column_config.NumberColumn("Sales · 180 days (£)", format="%.2f"),
                       "repeat_probability":st.column_config.ProgressColumn("Repeat propensity", min_value=0, max_value=1, format="%.2f")})
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
    importance["feature"] = importance.feature.str.replace("_", " ").str.replace("180d", "(180 days)").str.capitalize()
    chart(px.bar(importance, x="importance", y="feature", error_x="std", orientation="h", labels={"importance":"Holdout AP decrease after permutation", "feature":""}), 340)
    st.caption("Permutation importance measures sensitivity, not causality. Correlated features can share importance. Test data is used for final reporting only, not model selection.")
    with st.expander("Full comparison and limitations"):
        data_table(metrics)
        st.markdown("One retailer, 2010–2011, wholesale activity, and limited season coverage restrict generalization. Missing IDs exclude some purchases from modeling. Bootstrap uncertainty covers customers in one test snapshot, not future economic regimes. No causal uplift, automated outreach, or realized savings are claimed.")
    st.subheader("Monitor the scoring population")
    drift = load("feature_drift")
    drift["feature"] = drift.feature.str.replace("_", " ").str.replace("180d", "(180 days)").str.capitalize()
    data_table(drift)
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
    data_table(evidence)
    st.caption("Answers are calculated from the same sales tables used throughout the dashboard. Choose a question to see its supporting figures.")
    st.download_button("Download executive brief", (ROOT / "reports/executive_brief.md").read_text(), "retailsignal_brief.md", "text/markdown")

st.markdown('<div class="footer"><span><strong>retailsignal.</strong> &nbsp; A retail analytics study by Sree Vidya Cheekuri</span><a href="https://github.com/vidyacheekuri/retailsignal" target="_blank" rel="noopener noreferrer">Source & methodology ↗</a></div>', unsafe_allow_html=True)

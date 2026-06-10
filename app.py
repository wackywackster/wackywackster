"""SpaceX IPO Impact Dashboard — institutional-style market analysis.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from dashboard import analytics, charts, scenarios
from dashboard.config import (
    ACTUAL_IPO_VALUATION_B,
    DEFAULT_BENCHMARK,
    DEFAULT_FREE_FLOAT_PCT,
    DEFAULT_LOOKBACK_YEARS,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_SELECTION,
    EVENT_WINDOW_DAYS,
    IPO_CASE_STUDIES,
    IPO_DATE,
    IPO_VALUATION_SCENARIOS_B,
    POST_EVENT_WINDOWS,
    PRE_EVENT_WINDOWS,
    TICKER_GROUP,
    TICKER_NAME,
    UNIVERSE,
)
from dashboard.data import load_history, load_market_caps

st.set_page_config(
    page_title="SpaceX IPO Impact Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem;}
    [data-testid="stMetricValue"] {font-size: 1.4rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar — interactive filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🚀 SpaceX IPO Monitor")
    st.caption("Investment research dashboard — market impact of a prospective SpaceX listing.")

    ipo_date: date = st.date_input(
        "Assumed / announced IPO date",
        value=IPO_DATE,
        help="Single source of truth for all analysis periods and event windows. "
             "Defaults to dashboard/config.py → IPO_DATE.",
    )

    st.divider()
    st.subheader("Filters")

    default_start = date.today() - timedelta(days=365 * DEFAULT_LOOKBACK_YEARS)
    date_range = st.date_input(
        "Date range",
        value=(default_start, date.today()),
        max_value=date.today(),
    )
    start_date, end_date = (date_range if len(date_range) == 2
                            else (date_range[0], date.today()))

    groups = sorted({s.group for s in UNIVERSE})
    selected: list[str] = st.multiselect(
        "Securities",
        options=[s.ticker for s in UNIVERSE],
        default=DEFAULT_SELECTION,
        format_func=lambda t: f"{TICKER_NAME[t]} ({t}) — {TICKER_GROUP[t]}",
    )

    benchmark = st.selectbox(
        "Benchmark",
        options=["^GSPC", "^NDX", "^RUT", "ITA"],
        index=0,
        format_func=lambda t: TICKER_NAME[t],
    )

    valuation_b = st.select_slider(
        "SpaceX IPO valuation assumption",
        options=IPO_VALUATION_SCENARIOS_B,
        value=ACTUAL_IPO_VALUATION_B,
        format_func=lambda v: f"${v:,}B" + (" (actual)" if v == ACTUAL_IPO_VALUATION_B else ""),
    )

    with st.expander("Advanced assumptions"):
        risk_free = st.number_input("Risk-free rate (annual, %)", 0.0, 10.0,
                                    DEFAULT_RISK_FREE_RATE * 100, 0.25) / 100
        free_float = st.slider("SpaceX free float at IPO (%)", 5, 50,
                               int(DEFAULT_FREE_FLOAT_PCT * 100)) / 100
        event_window = st.slider("IPO event window (± trading days)", 5, 30,
                                 EVENT_WINDOW_DAYS)

if not selected:
    st.warning("Select at least one security in the sidebar.")
    st.stop()

# Always load the benchmark so relative metrics work even if it's deselected.
load_set = tuple(dict.fromkeys(selected + [benchmark, DEFAULT_BENCHMARK]))
data = load_history(load_set, start_date, end_date)
close, volume = data["close"], data["volume"]

if close.empty:
    st.error("No market data could be downloaded. Check connectivity and try again.")
    st.stop()

missing = [t for t in load_set if t not in close.columns]
if missing:
    st.sidebar.warning("No data for: " + ", ".join(missing))

shown = [t for t in selected if t in close.columns]
close_sel = close[shown]
volume_sel = volume[[t for t in shown if t in volume.columns]]
returns = analytics.daily_returns(close)
returns_sel = returns[shown]

ipo_in_range = pd.Timestamp(ipo_date) <= close.index.max()
ipo_passed = pd.Timestamp(ipo_date) <= pd.Timestamp(date.today())

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("SpaceX IPO Impact Dashboard")
st.caption(
    f"Assumed IPO date: **{ipo_date:%d %b %Y}** · "
    f"Valuation scenario: **${valuation_b:,}B** · "
    f"Benchmark: **{TICKER_NAME[benchmark]}** · "
    f"Data: {close.index.min():%d %b %Y} – {close.index.max():%d %b %Y} (Yahoo Finance, adjusted close)"
)
if not ipo_passed:
    days_to_ipo = (pd.Timestamp(ipo_date) - pd.Timestamp(date.today())).days
    st.info(f"⏳ The assumed IPO date is **{days_to_ipo} calendar days away**. "
            "IPO-event and post-IPO sections will populate automatically once the date passes — "
            "update `IPO_DATE` in `dashboard/config.py` (or the sidebar) when SpaceX confirms.")

kpi_cols = st.columns(4)
bench_close = close[benchmark].dropna()
kpis = [
    (f"{TICKER_NAME[benchmark]} (period)", bench_close.iloc[-1] / bench_close.iloc[0] - 1),
]
for t in ["ITA", "RKLB", "TSLA"]:
    if t in close.columns:
        s = close[t].dropna()
        kpis.append((f"{TICKER_NAME[t]} (period)", s.iloc[-1] / s.iloc[0] - 1))
for col, (label, val) in zip(kpi_cols, kpis):
    col.metric(label, f"{val:+.1%}")

tab_overview, tab_perf, tab_risk, tab_event, tab_scenario, tab_cases = st.tabs([
    "📊 Overview", "📈 Performance", "⚠️ Risk & Correlation",
    "🎯 Event Study", "🧮 IPO Scenarios", "📚 IPO Case Studies",
])

# ---------------------------------------------------------------------------
# Overview — three analysis periods
# ---------------------------------------------------------------------------
with tab_overview:
    st.subheader("Analysis periods")
    st.markdown(
        f"The dashboard splits history into three regimes anchored on the IPO date: "
        f"**Pre-IPO** (up to T−{event_window}), **IPO Event** (T−{event_window} to T+{event_window} "
        f"trading days), and **Post-IPO** (beyond T+{event_window})."
    )
    periods = analytics.split_periods(close_sel, ipo_date, event_window)
    pcols = st.columns(3)
    for col, (name, frame) in zip(pcols, periods.items()):
        with col:
            if frame.dropna(how="all").empty or len(frame) < 2:
                st.metric(name, "—", help="No data in this period yet.")
                st.caption("Awaiting data — populates once the IPO date passes.")
                continue
            st.metric(name, f"{len(frame)} sessions",
                      help=f"{frame.index.min():%d %b %Y} – {frame.index.max():%d %b %Y}")
            period_ret = (frame.dropna(how="all").apply(
                lambda s: s.dropna().iloc[-1] / s.dropna().iloc[0] - 1
                if s.dropna().size > 1 else np.nan))
            st.dataframe(
                period_ret.rename("Total return").rename(index=TICKER_NAME)
                .to_frame().style.format("{:+.1%}", na_rep="—")
                .background_gradient(cmap="RdYlGn"),
                width="stretch", height=320,
            )

    st.subheader("Performance & risk summary")
    st.caption(f"Full selected range · risk-free {risk_free:.2%} · alpha/beta vs S&P 500")
    table = analytics.summary_table(close_sel.join(close[[DEFAULT_BENCHMARK]], how="left", rsuffix="_dup")
                                    [shown if DEFAULT_BENCHMARK in shown else shown + [DEFAULT_BENCHMARK]],
                                    DEFAULT_BENCHMARK, risk_free)
    st.dataframe(charts.styled_metric_table(table.loc[[t for t in table.index if t in shown]]),
                 width="stretch")

# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
with tab_perf:
    st.plotly_chart(
        charts.line_chart(analytics.cumulative_returns(close_sel),
                          "Cumulative total return", "Cumulative return",
                          ipo_date=ipo_date if ipo_in_range else None),
        width="stretch")

    rel = analytics.relative_performance(close_sel.join(close[[benchmark]], how="left", rsuffix="_b")
                                         [list(dict.fromkeys(shown + [benchmark]))], benchmark)
    st.plotly_chart(
        charts.line_chart(rel, f"Relative performance vs {TICKER_NAME[benchmark]}",
                          "Excess cumulative return",
                          ipo_date=ipo_date if ipo_in_range else None),
        width="stretch")

    st.plotly_chart(
        charts.daily_returns_chart(returns_sel, "Daily returns",
                                   ipo_date=ipo_date if ipo_in_range else None),
        width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        if not volume_sel.dropna(how="all").empty:
            st.plotly_chart(
                charts.volume_chart(volume_sel, "Trading volume (21-day average)",
                                    ipo_date=ipo_date if ipo_in_range else None),
                width="stretch")
        else:
            st.info("Volume data unavailable for the current selection (indices report no volume).")
    with c2:
        caps = load_market_caps(tuple(shown))
        if not caps.empty:
            st.plotly_chart(
                charts.market_cap_bars(
                    caps, "Market capitalisation comparison",
                    scenario_caps_b={f"SpaceX @ ${valuation_b:,}B (scenario)": float(valuation_b)}),
                width="stretch")
        else:
            st.info("Market-cap data unavailable.")

# ---------------------------------------------------------------------------
# Risk & correlation
# ---------------------------------------------------------------------------
with tab_risk:
    vol_window = st.radio("Volatility window (trading days)", [21, 63, 126],
                          horizontal=True)
    st.plotly_chart(
        charts.line_chart(analytics.rolling_volatility(returns_sel, vol_window),
                          f"Rolling {vol_window}-day annualised volatility",
                          "Annualised volatility",
                          ipo_date=ipo_date if ipo_in_range else None),
        width="stretch")

    st.plotly_chart(
        charts.line_chart(analytics.drawdown(close_sel), "Drawdown from peak",
                          "Drawdown", ipo_date=ipo_date if ipo_in_range else None),
        width="stretch")

    st.subheader("Correlation of daily returns")
    corr_periods = analytics.split_periods(close_sel, ipo_date, event_window)
    options = ["Full range"] + [k for k, v in corr_periods.items() if len(v) > 20]
    corr_choice = st.radio("Correlation period", options, horizontal=True)
    corr_data = (returns_sel if corr_choice == "Full range"
                 else analytics.daily_returns(corr_periods[corr_choice]))
    st.plotly_chart(
        charts.correlation_heatmap(corr_data, f"Correlation matrix — {corr_choice}"),
        width="stretch")

# ---------------------------------------------------------------------------
# Event study
# ---------------------------------------------------------------------------
with tab_event:
    st.subheader("Event study around the SpaceX IPO date")
    st.markdown(
        "Total returns over standard event windows in **trading days** relative to "
        f"the IPO date (T0 = {ipo_date:%d %b %Y}). Pre-IPO windows measure positioning "
        "into the listing; post-IPO windows measure the aftermath."
    )
    es = analytics.event_study(close_sel, ipo_date, PRE_EVENT_WINDOWS, POST_EVENT_WINDOWS)
    if es.notna().any().any():
        st.plotly_chart(charts.event_study_bars(es, "Event-window total returns"),
                        width="stretch")
        st.dataframe(
            es.rename(index=TICKER_NAME).style.format("{:+.1%}", na_rep="awaiting data")
            .background_gradient(cmap="RdYlGn", axis=None),
            width="stretch")
        if es[[c for c in es.columns if c.startswith("T0")]].isna().all().all():
            st.caption("Post-IPO windows show *awaiting data* until the IPO date passes "
                       "and enough history accrues.")
    else:
        st.info("No event-window data yet — the assumed IPO date sits outside the loaded "
                "history. Extend the date range or wait for the listing.")

# ---------------------------------------------------------------------------
# Scenario modelling
# ---------------------------------------------------------------------------
with tab_scenario:
    st.subheader("Index-inclusion scenarios")
    st.markdown(
        f"Estimated weights assume **{free_float:.0%} free float** (S&P and Nasdaq use "
        "float-adjusted market caps) and approximate index totals from "
        "`dashboard/config.py`. SpaceX would be ineligible for the Russell 2000 "
        "(small-cap index) at every scenario."
    )
    table = scenarios.index_weight_table(IPO_VALUATION_SCENARIOS_B, free_float)
    st.plotly_chart(
        charts.scenario_weight_chart(table, "Estimated index weight by valuation scenario"),
        width="stretch")
    st.dataframe(
        table.style.format({
            "Float-Adj. Cap ($B)": "${:,.0f}B",
            **{c: "{:.3%}" for c in table.columns if c.endswith("Weight")},
        }, na_rep="Not eligible"),
        width="stretch")

    st.success(f"**${valuation_b:,}B scenario:** {scenarios.rank_context(valuation_b)}")

    st.markdown(
        """
        **Mechanical flow considerations**
        - *S&P 500 inclusion* requires positive GAAP earnings and a seasoning period —
          realistic 6–12 months post-IPO, triggering passive buying of roughly
          *(index weight × ~$13T of S&P-indexed assets)*.
        - *Nasdaq 100 inclusion* is faster (no profitability test) if SpaceX lists on Nasdaq.
        - Pure-play space names (RKLB, ASTS, LUNR, RDW, PL) face potential **flow rotation**:
          SpaceX would become the default institutional vehicle for space exposure.
        """
    )

# ---------------------------------------------------------------------------
# Historical IPO case studies
# ---------------------------------------------------------------------------
with tab_cases:
    st.subheader("What happened around past mega-IPOs?")
    st.markdown(
        "Each case shows the new listing, its sector ETF, and the S&P 500 aligned in "
        "event time (T0 = IPO). The summary table compares **sector** performance in the "
        "90 trading days before and after each listing to surface common patterns."
    )

    case_tickers = tuple(sorted({c.ticker for c in IPO_CASE_STUDIES}
                                | {c.sector_proxy for c in IPO_CASE_STUDIES}
                                | {"SPY"}))
    earliest = min(c.ipo_date for c in IPO_CASE_STUDIES) - timedelta(days=550)
    latest = max(c.ipo_date for c in IPO_CASE_STUDIES) + timedelta(days=550)
    case_data = load_history(case_tickers, earliest, min(latest, date.today()))
    case_close = case_data["close"]

    summary_rows = []
    for case in IPO_CASE_STUDIES:
        cols = [t for t in (case.ticker, case.sector_proxy, "SPY") if t in case_close.columns]
        es_case = analytics.event_study(case_close[cols], case.ipo_date, [-90], [90])
        row = {"IPO": f"{case.name} ({case.ipo_date:%b %Y})",
               "Offer valuation": f"${case.offer_valuation_b:,.0f}B",
               "Sector": case.sector_name}
        if case.sector_proxy in es_case.index:
            row["Sector −90d→IPO"] = es_case.loc[case.sector_proxy, "T-90 → T0"]
            row["Sector IPO→+90d"] = es_case.loc[case.sector_proxy, "T0 → T+90"]
        if case.ticker in es_case.index:
            row["Stock IPO→+90d"] = es_case.loc[case.ticker, "T0 → T+90"]
        if "SPY" in es_case.index:
            row["S&P 500 IPO→+90d"] = es_case.loc["SPY", "T0 → T+90"]
        summary_rows.append(row)

    if summary_rows:
        summary = pd.DataFrame(summary_rows).set_index("IPO")
        num_cols = [c for c in summary.columns if "→" in c]
        st.dataframe(
            summary.style.format({c: "{:+.1%}" for c in num_cols}, na_rep="—")
            .background_gradient(cmap="RdYlGn", subset=num_cols),
            width="stretch")

        valid = summary[num_cols].apply(pd.to_numeric, errors="coerce")
        if valid.notna().any().any():
            pre = valid.get("Sector −90d→IPO")
            post = valid.get("Sector IPO→+90d")
            stock = valid.get("Stock IPO→+90d")
            st.markdown(
                f"""
                **Common patterns across the five cases**
                - Sector ETFs averaged **{pre.mean():+.1%}** in the 90 trading days *into* the IPO
                  and **{post.mean():+.1%}** in the 90 days after — sector impact is usually modest;
                  mega-IPOs rarely sink their sector.
                - The IPO stocks themselves averaged **{stock.mean():+.1%}** in their first 90
                  sessions, with enormous dispersion ({stock.min():+.0%} to {stock.max():+.0%}):
                  buying the listing day has historically been a coin-flip dominated by the
                  prevailing market regime (compare ABNB/SNOW in the 2020 liquidity wave vs
                  META 2012 and UBER 2019).
                - **Read-through for SpaceX:** expect pre-IPO speculative bid in pure-play space
                  names (the "sympathy trade"), elevated sector volatility into the pricing, and
                  post-listing rotation *out of* proxies once direct exposure exists.
                """
            )

    st.divider()
    case_pick = st.selectbox(
        "Inspect a case in event time",
        options=[c.name for c in IPO_CASE_STUDIES])
    case = next(c for c in IPO_CASE_STUDIES if c.name == case_pick)
    cols = [t for t in (case.ticker, case.sector_proxy, "SPY") if t in case_close.columns]
    aligned = analytics.event_aligned_paths(case_close[cols], case.ipo_date,
                                            pre=90, post=252)
    if not aligned.empty:
        name_map = {case.ticker: f"{case.name} ({case.ticker})",
                    case.sector_proxy: case.sector_name, "SPY": "S&P 500 (SPY)"}
        st.plotly_chart(
            charts.aligned_event_chart(
                aligned, f"{case.name} IPO ({case.ipo_date:%d %b %Y}) — event-time performance",
                name_map=name_map),
            width="stretch")
        st.caption(f"💡 {case.note}")
    else:
        st.info("No data available for this case study window.")

st.divider()
st.caption(
    "Source: Yahoo Finance via yfinance · Prices are dividend/split-adjusted closes · "
    "Index weights are estimates based on static index-cap assumptions in config.py · "
    "For research purposes only — not investment advice."
)

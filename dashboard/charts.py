"""Plotly chart builders with a consistent institutional look."""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .config import TICKER_COLOR, TICKER_NAME

TEMPLATE = "plotly_white"
FONT = dict(family="Inter, Segoe UI, Helvetica, Arial, sans-serif", size=12)
MARGIN = dict(l=10, r=10, t=48, b=10)


def _base_layout(fig: go.Figure, title: str, ytitle: str,
                 yformat: str | None = ".1%") -> go.Figure:
    fig.update_layout(
        template=TEMPLATE,
        title=dict(text=title, font=dict(size=16)),
        font=FONT,
        margin=MARGIN,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis=dict(title=ytitle, tickformat=yformat),
        xaxis=dict(title=None),
    )
    return fig


def _add_ipo_marker(fig: go.Figure, ipo_date: date) -> go.Figure:
    ts = pd.Timestamp(ipo_date)
    fig.add_vline(x=ts, line_dash="dash", line_color="#d62728", line_width=1.5)
    fig.add_annotation(x=ts, yref="paper", y=1.0, text="IPO",
                       showarrow=False, font=dict(color="#d62728", size=11),
                       yanchor="bottom")
    return fig


def line_chart(df: pd.DataFrame, title: str, ytitle: str,
               ipo_date: date | None = None, yformat: str | None = ".1%") -> go.Figure:
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], mode="lines",
            name=TICKER_NAME.get(col, col),
            line=dict(color=TICKER_COLOR.get(col), width=1.6),
        ))
    _base_layout(fig, title, ytitle, yformat)
    if ipo_date is not None:
        _add_ipo_marker(fig, ipo_date)
    return fig


def daily_returns_chart(returns: pd.DataFrame, title: str,
                        ipo_date: date | None = None) -> go.Figure:
    fig = go.Figure()
    for col in returns.columns:
        fig.add_trace(go.Bar(
            x=returns.index, y=returns[col],
            name=TICKER_NAME.get(col, col),
            marker_color=TICKER_COLOR.get(col),
            opacity=0.75,
        ))
    _base_layout(fig, title, "Daily return", ".1%")
    fig.update_layout(barmode="overlay")
    if ipo_date is not None:
        _add_ipo_marker(fig, ipo_date)
    return fig


def correlation_heatmap(returns: pd.DataFrame, title: str) -> go.Figure:
    corr = returns.corr()
    labels = [TICKER_NAME.get(t, t) for t in corr.columns]
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=labels, y=labels,
        zmin=-1, zmax=1, colorscale="RdBu_r",
        text=corr.round(2).values, texttemplate="%{text}",
        colorbar=dict(title="ρ"),
    ))
    fig.update_layout(template=TEMPLATE, title=dict(text=title, font=dict(size=16)),
                      font=FONT, margin=MARGIN, height=max(420, 32 * len(labels)))
    return fig


def event_study_bars(table: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    for window in table.columns:
        fig.add_trace(go.Bar(
            x=[TICKER_NAME.get(t, t) for t in table.index],
            y=table[window], name=window,
        ))
    _base_layout(fig, title, "Total return", ".0%")
    fig.update_layout(barmode="group", xaxis=dict(tickangle=-30))
    return fig


def volume_chart(volume: pd.DataFrame, title: str,
                 ipo_date: date | None = None, window: int = 21) -> go.Figure:
    smoothed = volume.rolling(window).mean()
    fig = line_chart(smoothed, title, f"{window}d avg shares traded",
                     ipo_date=ipo_date, yformat="~s")
    return fig


def market_cap_bars(caps: pd.Series, title: str,
                    scenario_caps_b: dict[str, float] | None = None) -> go.Figure:
    df = (caps / 1e9).sort_values(ascending=True)
    names = [TICKER_NAME.get(t, t) for t in df.index]
    colors = [TICKER_COLOR.get(t, "#1f77b4") for t in df.index]
    fig = go.Figure(go.Bar(x=df.values, y=names, orientation="h",
                           marker_color=colors, name="Current"))
    if scenario_caps_b:
        for label, v in scenario_caps_b.items():
            fig.add_trace(go.Bar(x=[v], y=[label], orientation="h",
                                 marker_color="#d62728", name=label))
    fig.update_layout(template=TEMPLATE, title=dict(text=title, font=dict(size=16)),
                      font=FONT, margin=MARGIN, showlegend=False,
                      xaxis=dict(title="Market cap ($B, log scale)", type="log"),
                      height=max(420, 30 * (len(df) + len(scenario_caps_b or {}))))
    return fig


def aligned_event_chart(aligned: pd.DataFrame, title: str,
                        name_map: dict[str, str] | None = None) -> go.Figure:
    names = name_map or TICKER_NAME
    fig = go.Figure()
    for col in aligned.columns:
        fig.add_trace(go.Scatter(
            x=aligned.index, y=aligned[col], mode="lines",
            name=names.get(col, col),
            line=dict(width=1.8),
        ))
    _base_layout(fig, title, "Cumulative return", ".0%")
    fig.update_layout(xaxis=dict(title="Trading days relative to IPO (T0 = listing)"))
    fig.add_vline(x=0, line_dash="dash", line_color="#d62728", line_width=1.5)
    return fig


def scenario_weight_chart(table: pd.DataFrame, title: str) -> go.Figure:
    weight_cols = [c for c in table.columns if c.endswith("Weight")]
    fig = go.Figure()
    for c in weight_cols:
        fig.add_trace(go.Bar(x=table.index, y=table[c],
                             name=c.replace(" Weight", "")))
    _base_layout(fig, title, "Estimated index weight", ".2%")
    fig.update_layout(barmode="group")
    return fig


def styled_metric_table(df: pd.DataFrame):
    """Format a metrics DataFrame for st.dataframe with % styling."""
    pct_cols = [c for c in df.columns if c not in ("Sharpe Ratio", "Beta vs S&P 500")]
    fmt = {c: "{:+.1%}" for c in pct_cols}
    fmt["Sharpe Ratio"] = "{:.2f}"
    fmt["Beta vs S&P 500"] = "{:.2f}"
    return (df.rename(index=lambda t: TICKER_NAME.get(t, t))
              .style.format(fmt, na_rep="—")
              .background_gradient(cmap="RdYlGn", axis=0, subset=[c for c in df.columns if c != "Beta vs S&P 500"]))


def px_colors():
    return px.colors.qualitative.D3

"""Quantitative analytics: returns, risk metrics, event studies."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .config import TRADING_DAYS_PER_YEAR


# ---------------------------------------------------------------------------
# Return transformations
# ---------------------------------------------------------------------------
def daily_returns(close: pd.DataFrame) -> pd.DataFrame:
    return close.pct_change().dropna(how="all")


def cumulative_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Growth of 1 unit, rebased to the first valid observation per column."""
    rebased = close / close.apply(lambda s: s.loc[s.first_valid_index()] if s.first_valid_index() is not None else np.nan)
    return rebased - 1.0


def rolling_volatility(returns: pd.DataFrame, window: int = 21) -> pd.DataFrame:
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def drawdown(close: pd.DataFrame) -> pd.DataFrame:
    running_max = close.cummax()
    return close / running_max - 1.0


def relative_performance(close: pd.DataFrame, benchmark: str) -> pd.DataFrame:
    """Cumulative return of each security minus the benchmark's."""
    cum = cumulative_returns(close)
    if benchmark not in cum.columns:
        return pd.DataFrame(index=cum.index)
    rel = cum.sub(cum[benchmark], axis=0)
    return rel.drop(columns=[benchmark])


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------
def cagr(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 2 or s.iloc[0] <= 0:
        return np.nan
    years = len(s) / TRADING_DAYS_PER_YEAR
    return (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan


def annualised_volatility(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) < 2:
        return np.nan
    return r.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return np.nan
    excess = r - risk_free_rate / TRADING_DAYS_PER_YEAR
    return excess.mean() / r.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def max_drawdown(close: pd.Series) -> float:
    s = close.dropna()
    if len(s) < 2:
        return np.nan
    return float(drawdown(s.to_frame()).min().iloc[0])


def alpha_beta(returns: pd.Series, benchmark_returns: pd.Series,
               risk_free_rate: float) -> tuple[float, float]:
    """CAPM alpha (annualised) and beta versus the benchmark."""
    df = pd.concat([returns, benchmark_returns], axis=1, keys=["asset", "bench"]).dropna()
    if len(df) < 20 or df["bench"].var() == 0:
        return np.nan, np.nan
    rf_daily = risk_free_rate / TRADING_DAYS_PER_YEAR
    ex_asset = df["asset"] - rf_daily
    ex_bench = df["bench"] - rf_daily
    beta = ex_asset.cov(ex_bench) / ex_bench.var()
    alpha_daily = ex_asset.mean() - beta * ex_bench.mean()
    return alpha_daily * TRADING_DAYS_PER_YEAR, beta


def summary_table(close: pd.DataFrame, benchmark: str,
                  risk_free_rate: float) -> pd.DataFrame:
    """One row of performance/risk metrics per security."""
    rets = daily_returns(close)
    rows = {}
    bench_rets = rets[benchmark] if benchmark in rets.columns else pd.Series(dtype=float)
    for t in close.columns:
        a, b = alpha_beta(rets[t], bench_rets, risk_free_rate)
        s = close[t].dropna()
        rows[t] = {
            "Total Return": s.iloc[-1] / s.iloc[0] - 1 if len(s) > 1 else np.nan,
            "CAGR": cagr(close[t]),
            "Ann. Volatility": annualised_volatility(rets[t]),
            "Sharpe Ratio": sharpe_ratio(rets[t], risk_free_rate),
            "Max Drawdown": max_drawdown(close[t]),
            "Alpha vs S&P 500": a,
            "Beta vs S&P 500": b,
        }
    return pd.DataFrame(rows).T


# ---------------------------------------------------------------------------
# Analysis periods & event study
# ---------------------------------------------------------------------------
def split_periods(close: pd.DataFrame, ipo_date: date,
                  event_window: int) -> dict[str, pd.DataFrame]:
    """Split price history into Pre-IPO / IPO Event / Post-IPO periods.

    The event period spans ``event_window`` trading days either side of the
    IPO date; pre/post periods cover everything outside it.
    """
    idx = close.index
    ts = pd.Timestamp(ipo_date)
    if len(idx) == 0:
        return {"Pre-IPO": close, "IPO Event": close.iloc[0:0], "Post-IPO": close.iloc[0:0]}
    if ts > idx.max():
        # IPO is beyond the data: project its trading-day position so the
        # event window starts filling once we come within `event_window`
        # sessions of the listing (rather than never, or always).
        pos = len(idx) - 1 + len(pd.bdate_range(idx.max(), ts)) - 1
    else:
        pos = int(idx.searchsorted(ts))
    lo = max(min(pos - event_window, len(idx)), 0)
    hi = min(pos + event_window + 1, len(idx))
    return {
        "Pre-IPO": close.iloc[:lo],
        "IPO Event": close.iloc[lo:hi],
        "Post-IPO": close.iloc[hi:],
    }


def event_study(close: pd.DataFrame, ipo_date: date,
                pre_windows: list[int], post_windows: list[int]) -> pd.DataFrame:
    """Total returns over windows anchored on the IPO date (trading days).

    Pre windows: return from T-n through T0.  Post windows: T0 through T+n.
    Windows extending beyond the available history return NaN.
    """
    idx = close.index
    ts = pd.Timestamp(ipo_date)
    pos = int(idx.searchsorted(ts))
    anchor = min(pos, len(idx) - 1)

    def window_return(series: pd.Series, start_pos: int, end_pos: int) -> float:
        if start_pos < 0 or end_pos >= len(idx) or start_pos >= end_pos:
            return np.nan
        a, b = series.iloc[start_pos], series.iloc[end_pos]
        return b / a - 1 if pd.notna(a) and pd.notna(b) and a != 0 else np.nan

    out = {}
    for t in close.columns:
        row = {}
        for n in pre_windows:
            row[f"T{n} → T0"] = window_return(close[t], anchor + n, anchor)
        for n in post_windows:
            row[f"T0 → T+{n}"] = window_return(close[t], anchor, anchor + n)
        out[t] = row
    return pd.DataFrame(out).T


def event_aligned_paths(close: pd.DataFrame, event_dt: date,
                        pre: int = 60, post: int = 252) -> pd.DataFrame:
    """Cumulative returns re-indexed to trading days relative to an event.

    Day 0 is the first trading session on/after ``event_dt``; values are
    rebased so day -``pre`` (or first available day) equals 0.
    """
    idx = close.index
    pos = int(idx.searchsorted(pd.Timestamp(event_dt)))
    lo, hi = max(pos - pre, 0), min(pos + post + 1, len(idx))
    window = close.iloc[lo:hi]
    if window.empty:
        return pd.DataFrame()
    aligned = cumulative_returns(window)
    aligned.index = range(lo - pos, hi - pos)
    return aligned

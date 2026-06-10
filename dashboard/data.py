"""Market-data loading layer (yfinance) with Streamlit caching."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

CACHE_TTL_SECONDS = 60 * 60  # refresh market data hourly


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Downloading market data…")
def load_history(tickers: tuple[str, ...], start: date, end: date) -> dict[str, pd.DataFrame]:
    """Download OHLCV history for ``tickers``.

    Returns ``{"close": DataFrame, "volume": DataFrame}`` with one column per
    ticker, indexed by trading date.  Tickers that fail to download are
    silently dropped (the UI reports what actually loaded).
    """
    raw = yf.download(
        list(tickers),
        start=start,
        end=end + timedelta(days=1),
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    close = pd.DataFrame(index=raw.index)
    volume = pd.DataFrame(index=raw.index)
    for t in tickers:
        try:
            frame = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            if frame["Close"].notna().any():
                close[t] = frame["Close"]
                volume[t] = frame["Volume"]
        except (KeyError, TypeError):
            continue
    close = close.dropna(how="all")
    volume = volume.reindex(close.index)
    return {"close": close, "volume": volume}


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_market_caps(tickers: tuple[str, ...]) -> pd.Series:
    """Fetch current market capitalisations (USD).  Indices return NaN."""
    caps: dict[str, float] = {}
    for t in tickers:
        if t.startswith("^"):
            continue
        try:
            info = yf.Ticker(t).fast_info
            cap = getattr(info, "market_cap", None)
            if cap:
                caps[t] = float(cap)
        except Exception:
            continue
    return pd.Series(caps, dtype="float64")

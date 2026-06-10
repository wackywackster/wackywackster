"""Central configuration for the SpaceX IPO Impact Dashboard.

Every assumption that an analyst may want to change lives here.  The single
most important variable is ``IPO_DATE``: when the actual SpaceX IPO date is
announced, update that one value and the entire dashboard (analysis periods,
event-study windows, scenario tables) re-anchors automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------------------
# THE single configurable IPO date.
# Confirmed: SpaceX lists on Nasdaq as SPCX on 12 June 2026 at $135/share
# (~$1.77T initial market cap).  Adjust here if the listing slips.
# ---------------------------------------------------------------------------
IPO_DATE: date = date(2026, 6, 12)

# SpaceX ticker once trading begins.
SPACEX_TICKER: str = "SPCX"

# Length of the "IPO event period" in trading days either side of the listing.
EVENT_WINDOW_DAYS: int = 10

# Default history to load before the earliest analysis window.
DEFAULT_LOOKBACK_YEARS: int = 3

# Annual risk-free rate used for Sharpe ratio / alpha (decimal).
DEFAULT_RISK_FREE_RATE: float = 0.04

TRADING_DAYS_PER_YEAR: int = 252


@dataclass(frozen=True)
class Security:
    ticker: str
    name: str
    group: str
    color: str


# ---------------------------------------------------------------------------
# Universe definition
# ---------------------------------------------------------------------------
BENCHMARKS: list[Security] = [
    Security("^GSPC", "S&P 500", "Benchmark", "#1f77b4"),
    Security("^NDX", "Nasdaq 100", "Benchmark", "#9467bd"),
    Security("^RUT", "Russell 2000", "Benchmark", "#8c564b"),
]

SECTOR_PROXIES: list[Security] = [
    Security("ITA", "iShares U.S. Aerospace & Defense", "Aerospace & Defense", "#2ca02c"),
    Security("XAR", "SPDR S&P Aerospace & Defense", "Aerospace & Defense", "#98df8a"),
]

SPACE_COMPANIES: list[Security] = [
    Security("RKLB", "Rocket Lab", "Space Companies", "#d62728"),
    Security("ASTS", "AST SpaceMobile", "Space Companies", "#ff7f0e"),
    Security("IRDM", "Iridium Communications", "Space Companies", "#17becf"),
    Security("LUNR", "Intuitive Machines", "Space Companies", "#e377c2"),
    Security("RDW", "Redwire", "Space Companies", "#bcbd22"),
    Security("PL", "Planet Labs", "Space Companies", "#7f7f7f"),
]

RELATED: list[Security] = [
    Security("TSLA", "Tesla", "Musk Ecosystem", "#aec7e8"),
]

# SpaceX itself (no price history until the 12 Jun 2026 listing) plus funds
# with disclosed pre-IPO SpaceX exposure.
SPACEX_EXPOSURE: list[Security] = [
    Security("SPCX", "SpaceX", "SpaceX", "#000000"),
    Security("XOVR", "ERShares Private-Public Crossover ETF (holds SpaceX)", "SpaceX Exposure", "#ffbb78"),
    Security("DXYZ", "Destiny Tech100 (holds SpaceX)", "SpaceX Exposure", "#c49c94"),
    Security("ARKX", "ARK Space Exploration ETF", "SpaceX Exposure", "#f7b6d2"),
]

UNIVERSE: list[Security] = BENCHMARKS + SECTOR_PROXIES + SPACE_COMPANIES + RELATED + SPACEX_EXPOSURE

TICKER_NAME: dict[str, str] = {s.ticker: s.name for s in UNIVERSE}
TICKER_COLOR: dict[str, str] = {s.ticker: s.color for s in UNIVERSE}
TICKER_GROUP: dict[str, str] = {s.ticker: s.group for s in UNIVERSE}

DEFAULT_BENCHMARK: str = "^GSPC"

# Tickers shown by default when the app first loads.
DEFAULT_SELECTION: list[str] = [
    "^GSPC", "^NDX", "^RUT", "ITA",
    "RKLB", "ASTS", "IRDM", "LUNR", "RDW", "PL",
    "TSLA", "XOVR", "SPCX",
]

# ---------------------------------------------------------------------------
# Scenario modelling assumptions (USD billions unless stated otherwise)
# ---------------------------------------------------------------------------
# Hypothetical scenarios plus the actual priced valuation (~$1.77T at $135/share).
IPO_VALUATION_SCENARIOS_B: list[int] = [200, 300, 500, 1000, 1770]
ACTUAL_IPO_VALUATION_B: int = 1770

# Approximate total float-adjusted market capitalisations of the major
# indices (USD billions).  Update periodically — these drive the estimated
# index-weight calculations, not any live computation.
INDEX_TOTAL_MCAP_B: dict[str, float] = {
    "S&P 500": 52_000.0,
    "Nasdaq 100": 25_000.0,
    "Russell 2000": 2_400.0,
}

# Assumed free float sold / available at IPO (S&P uses float-adjusted caps).
DEFAULT_FREE_FLOAT_PCT: float = 0.15

# ---------------------------------------------------------------------------
# Event-study windows (trading days relative to IPO date)
# ---------------------------------------------------------------------------
PRE_EVENT_WINDOWS: list[int] = [-252, -90, -30]
POST_EVENT_WINDOWS: list[int] = [30, 90, 252]

# ---------------------------------------------------------------------------
# Historical IPO case studies
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IPOCase:
    ticker: str
    name: str
    ipo_date: date
    offer_valuation_b: float  # approx. valuation at listing, USD billions
    sector_proxy: str         # ETF representing the company's sector
    sector_name: str
    note: str


IPO_CASE_STUDIES: list[IPOCase] = [
    IPOCase("META", "Meta Platforms", date(2012, 5, 18), 104.0, "XLK", "Technology (XLK)",
            "Largest tech IPO of its time; fell ~50% in 3 months before a historic recovery."),
    IPOCase("UBER", "Uber Technologies", date(2019, 5, 10), 82.0, "XLK", "Technology (XLK)",
            "Priced below range; traded under the offer price for most of its first year."),
    IPOCase("ABNB", "Airbnb", date(2020, 12, 10), 47.0, "XLY", "Consumer Discretionary (XLY)",
            "Doubled on day one during the 2020 IPO frenzy."),
    IPOCase("SNOW", "Snowflake", date(2020, 9, 16), 33.0, "XLK", "Technology (XLK)",
            "Largest software IPO ever at the time; opened ~104% above offer."),
    IPOCase("COIN", "Coinbase", date(2021, 4, 14), 86.0, "XLF", "Financials (XLF)",
            "Direct listing that top-ticked the 2021 crypto cycle."),
]

CASE_STUDY_SECTOR_PROXIES: dict[str, str] = {
    "XLK": "Technology Select Sector SPDR",
    "XLY": "Consumer Discretionary Select Sector SPDR",
    "XLF": "Financial Select Sector SPDR",
}

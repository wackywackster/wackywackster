# SpaceX IPO Impact Dashboard 🚀

An institutional-investor style Streamlit dashboard analysing the market impact of a
prospective SpaceX IPO across benchmarks, the aerospace & defense sector, pure-play
space companies, Tesla, and funds with disclosed SpaceX exposure.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuring the IPO date

The entire dashboard is anchored on **one variable**:

```python
# dashboard/config.py
IPO_DATE: date = date(2026, 12, 15)
```

When SpaceX announces the actual listing date, change that value (or override it
live via the sidebar date picker) — analysis periods, event-study windows and
scenario tables all re-anchor automatically. Post-IPO sections display
*awaiting data* until the date passes.

## What's inside

| Tab | Contents |
| --- | --- |
| **Overview** | Pre-IPO / IPO-event / Post-IPO period returns; CAGR, Sharpe, max drawdown, annualised volatility, alpha & beta vs S&P 500 |
| **Performance** | Cumulative returns, relative performance vs benchmark, daily returns, 21-day average volume, market-cap comparison incl. the SpaceX scenario bar |
| **Risk & Correlation** | Rolling volatility (21/63/126d), drawdown from peak, correlation matrices per analysis period |
| **Event Study** | Total returns over T−252/−90/−30 → T0 and T0 → T+30/+90/+252 trading-day windows |
| **IPO Scenarios** | Estimated S&P 500 / Nasdaq 100 weights at $200B, $300B, $500B and $1T valuations with a configurable free-float assumption |
| **IPO Case Studies** | Meta, Uber, Airbnb, Snowflake, Coinbase — sector performance before/after each listing, event-time charts, and common patterns |

## Coverage

- **Benchmarks:** S&P 500 (^GSPC), Nasdaq 100 (^NDX), Russell 2000 (^RUT)
- **Sector:** iShares (ITA) and SPDR (XAR) Aerospace & Defense ETFs
- **Space companies:** RKLB, ASTS, IRDM, LUNR, RDW, PL
- **Musk ecosystem:** TSLA
- **SpaceX exposure funds:** XOVR (ERShares Crossover), DXYZ (Destiny Tech100), ARKX

## Interactive filters

Date range, security selection, benchmark selection, IPO valuation assumption,
risk-free rate, free-float percentage and event-window length — all in the sidebar.

## Data & caveats

Data comes from Yahoo Finance via `yfinance` (hourly cache). Index-weight
estimates use static approximate index capitalisations in `dashboard/config.py`;
update them periodically. For research purposes only — not investment advice.
